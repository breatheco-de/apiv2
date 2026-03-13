from django.core.management.base import BaseCommand
from django.utils import timezone

from breathecode.admissions.models import Academy, CohortUser
from breathecode.assignments.models import Task
from breathecode.admissions.utils.academy_features import has_feature_flag
from breathecode.certificate.actions import (
    how_many_pending_tasks,
    generate_certificate,
    get_assets_from_syllabus,
)
from breathecode.certificate.models import UserSpecialty
from breathecode.authenticate.models import User


class Command(BaseCommand):
    help = "Aplica auto-ignore retroactivo a proyectos entregados y genera certificados para estudiantes que completaron el 100%"

    def add_arguments(self, parser):
        parser.add_argument(
            "--academy-id",
            type=int,
            help="ID de la academia específica (opcional, si no se especifica procesa todas)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ejecuta sin hacer cambios en la base de datos",
        )
        parser.add_argument(
            "--skip-certificates",
            action="store_true",
            help="Solo ignora proyectos, no genera certificados",
        )
        parser.add_argument(
            "--user-email",
            type=str,
            help="Email del usuario específico a procesar (opcional)",
        )

    def handle(self, *args, **options):
        academy_id = options.get("academy_id")
        dry_run = options.get("dry_run", False)
        skip_certificates = options.get("skip_certificates", False)
        user_email = options.get("user_email")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 MODO DRY-RUN: No se realizarán cambios"))

        # Si se especifica un email, buscar el usuario
        user_filter = None
        if user_email:
            try:
                user = User.objects.filter(email=user_email).first()
                if not user:
                    self.stdout.write(self.style.ERROR(f"⚠️  Usuario con email {user_email} no encontrado"))
                    return
                user_filter = user
                self.stdout.write(self.style.SUCCESS(f"✓ Usuario encontrado: {user.email} (ID: {user.id})"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"⚠️  Error buscando usuario: {str(e)}"))
                return

        # Buscar academias con el flag activado
        academies = Academy.objects.all()
        if academy_id:
            academies = academies.filter(id=academy_id)

        academies_with_flag = []
        for academy in academies:
            if has_feature_flag(academy, "certificate.auto_ignore_projects_on_delivery", default=False):
                academies_with_flag.append(academy)

        if not academies_with_flag:
            self.stdout.write(self.style.WARNING("⚠️  No se encontraron academias con el flag activado"))
            return

        self.stdout.write(
            self.style.SUCCESS(f"✓ Se encontraron {len(academies_with_flag)} academias con el flag activado")
        )

        total_projects_ignored = 0
        total_students_graduated = 0
        total_certificates_generated = 0
        total_errors = 0

        for academy in academies_with_flag:
            self.stdout.write(f"\n📚 Procesando academia: {academy.name} (ID: {academy.id})")

            # Buscar proyectos entregados que no estén IGNORED ni APPROVED
            # Solo proyectos de estudiantes en cohorts de esta academia
            projects_to_ignore = Task.objects.filter(
                task_type="PROJECT",
                task_status="DONE",
                cohort__academy=academy,
            ).exclude(revision_status__in=["IGNORED", "APPROVED"]).select_related("user", "cohort")
            
            # Si se especificó un usuario, filtrar por ese usuario
            if user_filter:
                projects_to_ignore = projects_to_ignore.filter(user=user_filter)

            projects_count = projects_to_ignore.count()
            if projects_count == 0:
                self.stdout.write(f"  ⏭️  No hay proyectos para ignorar en esta academia")
                continue

            self.stdout.write(f"  📦 Encontrados {projects_count} proyectos para ignorar")

            # Agrupar por usuario y cohort para procesar después
            projects_by_user_cohort = {}
            for project in projects_to_ignore:
                if not project.cohort or not project.user:
                    continue
                # Solo procesar proyectos con task_status="DONE"
                if project.task_status != "DONE":
                    continue
                key = (project.user_id, project.cohort_id)
                if key not in projects_by_user_cohort:
                    projects_by_user_cohort[key] = []
                projects_by_user_cohort[key].append(project)

            # Procesar cada usuario-cohort que tiene proyectos con task_status="DONE" para ignorar
            for (user_id, cohort_id), projects in projects_by_user_cohort.items():
                try:
                    # Ignorar proyectos (usar save() para que se disparen los signals)
                    if not dry_run:
                        for project in projects:
                            project.revision_status = "IGNORED"
                            project.reviewed_at = timezone.now()
                            project.save(update_fields=["revision_status", "reviewed_at"])
                            total_projects_ignored += 1
                    else:
                        total_projects_ignored += len(projects)
                        self.stdout.write(
                            f"    [DRY-RUN] Se ignorarían {len(projects)} proyectos del usuario {user_id}"
                        )

                    # Verificar si el estudiante completó el 100%
                    if not skip_certificates:
                        cohort_user = CohortUser.objects.filter(
                            user_id=user_id,
                            cohort_id=cohort_id,
                            role="STUDENT"
                        ).first()

                        if not cohort_user:
                            continue

                        cohort = cohort_user.cohort
                        if not cohort or not cohort.syllabus_version:
                            continue

                        # Verificar pending tasks (debe ser 0 después de ignorar)
                        # En modo DRY-RUN, necesitamos simular que los proyectos ya están ignorados
                        pending_tasks = how_many_pending_tasks(
                            cohort.syllabus_version,
                            cohort_user.user,
                            task_types=["PROJECT"],
                            only_mandatory=True,
                            cohort_id=cohort.id,
                        )
                        
                        # En modo DRY-RUN, restar los proyectos que vamos a ignorar
                        if dry_run:
                            # Contar cuántos de los proyectos que vamos a ignorar son obligatorios
                            mandatory_slugs = get_assets_from_syllabus(
                                cohort.syllabus_version,
                                task_types=["PROJECT"],
                                only_mandatory=True
                            )
                            projects_to_ignore_count = sum(
                                1 for p in projects 
                                if p.associated_slug in mandatory_slugs
                            )
                            pending_tasks = max(0, pending_tasks - projects_to_ignore_count)

                        if pending_tasks == 0:
                            # Graduar estudiante si no está graduado
                            if cohort_user.educational_status != "GRADUATED":
                                if not dry_run:
                                    cohort_user.educational_status = "GRADUATED"
                                    cohort_user.save(update_fields=["educational_status"])
                                total_students_graduated += 1
                                if not dry_run:
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f"    ✓ Estudiante {user_id} (CohortUser ID: {cohort_user.id}) graduado (cohort {cohort_id})"
                                        )
                                    )
                                else:
                                    self.stdout.write(
                                        f"    [DRY-RUN] Se graduaría al estudiante {user_id} (CohortUser ID: {cohort_user.id}, cohort {cohort_id})"
                                    )

                            # Generar certificado si no existe
                            existing_cert = UserSpecialty.objects.filter(
                                user_id=user_id,
                                cohort_id=cohort_id,
                                status="PERSISTED"
                            ).first()

                            if not existing_cert:
                                if not dry_run:
                                    try:
                                        generate_certificate(cohort_user.user, cohort)
                                        total_certificates_generated += 1
                                        self.stdout.write(
                                            self.style.SUCCESS(
                                                f"    ✓ Certificado generado para estudiante {user_id} (CohortUser ID: {cohort_user.id})"
                                            )
                                        )
                                    except Exception as e:
                                        total_errors += 1
                                        self.stdout.write(
                                            self.style.ERROR(
                                                f"    ✗ Error generando certificado para {user_id} (CohortUser ID: {cohort_user.id}): {str(e)}"
                                            )
                                        )
                                else:
                                    total_certificates_generated += 1
                                    self.stdout.write(
                                        f"    [DRY-RUN] Se generaría certificado para estudiante {user_id} (CohortUser ID: {cohort_user.id})"
                                    )
                            else:
                                self.stdout.write(
                                    f"    ⏭️  El estudiante {user_id} (CohortUser ID: {cohort_user.id}) ya tiene certificado"
                                )
                        else:
                            self.stdout.write(
                                f"    ⏭️  Estudiante {user_id} aún tiene {pending_tasks} tareas pendientes"
                            )

                except Exception as e:
                    total_errors += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"    ✗ Error procesando usuario {user_id}, cohort {cohort_id}: {str(e)}"
                        )
                    )

        # Resumen
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 RESUMEN"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Proyectos ignorados: {total_projects_ignored}")
        self.stdout.write(f"Estudiantes graduados: {total_students_graduated}")
        self.stdout.write(f"Certificados generados: {total_certificates_generated}")
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f"Errores: {total_errors}"))
        self.stdout.write("=" * 60)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n⚠️  Este fue un DRY-RUN. Ejecuta sin --dry-run para aplicar cambios")
            )
