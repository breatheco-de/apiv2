"""
Management command to seed talent development data for development.

This command creates sample data for:
- Skill Domains
- Skills
- Competencies
- Job Families
- Job Roles
- Career Paths
- Career Stages
- And their relationships

Usage:
    poetry run python manage.py seed_talent_development
    poetry run python manage.py seed_talent_development --clear  # Clear existing data first
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from breathecode.talent_development.models import (
    CareerPath,
    CareerStage,
    Competency,
    CompetencySkill,
    JobFamily,
    JobRole,
    Skill,
    SkillAttitudeTag,
    SkillBehaviorIndicator,
    SkillDomain,
    SkillKnowledgeItem,
    StageCompetency,
)


class Command(BaseCommand):
    help = "Seed talent development data for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing talent development data before seeding",
        )

    def handle(self, *args, **options):
        clear = options["clear"]
        verbosity = options.get("verbosity", 1)

        if clear:
            if verbosity >= 1:
                self.stdout.write(self.style.WARNING("Clearing existing talent development data..."))
            self._clear_data()
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS("✓ Data cleared"))

        if verbosity >= 1:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write("Seeding talent development data...")
            self.stdout.write("=" * 70 + "\n")

        with transaction.atomic():
            # Create Skill Domains
            if verbosity >= 1:
                self.stdout.write("Creating skill domains...")
            domains = self._create_skill_domains()
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(domains)} skill domains"))

            # Create Skills
            if verbosity >= 1:
                self.stdout.write("Creating skills...")
            skills = self._create_skills(domains)
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(skills)} skills"))

            # Create Competencies
            if verbosity >= 1:
                self.stdout.write("Creating competencies...")
            competencies = self._create_competencies()
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(competencies)} competencies"))

            # Link Skills to Competencies
            if verbosity >= 1:
                self.stdout.write("Linking skills to competencies...")
            competency_skills = self._create_competency_skills(competencies, skills)
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(competency_skills)} competency-skill links"))

            # Create Job Families
            if verbosity >= 1:
                self.stdout.write("Creating job families...")
            job_families = self._create_job_families()
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(job_families)} job families"))

            # Create Job Roles
            if verbosity >= 1:
                self.stdout.write("Creating job roles...")
            job_roles = self._create_job_roles(job_families)
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(job_roles)} job roles"))

            # Create Career Paths
            if verbosity >= 1:
                self.stdout.write("Creating career paths...")
            career_paths = self._create_career_paths(job_roles)
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(career_paths)} career paths"))

            # Create Career Stages
            if verbosity >= 1:
                self.stdout.write("Creating career stages...")
            career_stages = self._create_career_stages(career_paths)
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(career_stages)} career stages"))

            # Link Competencies to Stages
            if verbosity >= 1:
                self.stdout.write("Linking competencies to career stages...")
            stage_competencies = self._create_stage_competencies(career_stages, competencies)
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(stage_competencies)} stage-competency links"))

            # Create Skill Behavior Indicators
            if verbosity >= 1:
                self.stdout.write("Creating skill behavior indicators...")
            behavior_indicators = self._create_skill_behavior_indicators(skills)
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(behavior_indicators)} behavior indicators"))

            # Create Skill Knowledge Items
            if verbosity >= 1:
                self.stdout.write("Creating skill knowledge items...")
            knowledge_items = self._create_skill_knowledge_items(skills)
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(knowledge_items)} knowledge items"))

            # Create Skill Attitude Tags
            if verbosity >= 1:
                self.stdout.write("Creating skill attitude tags...")
            attitude_tags = self._create_skill_attitude_tags(skills)
            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {len(attitude_tags)} attitude tags"))

        if verbosity >= 1:
            self.stdout.write("\n" + "=" * 70)
            self.stdout.write(self.style.SUCCESS("✓ Talent development data seeded successfully!"))
            self.stdout.write("=" * 70 + "\n")

    def _clear_data(self):
        """Clear all talent development data"""
        StageCompetency.objects.all().delete()
        CompetencySkill.objects.all().delete()
        SkillAttitudeTag.objects.all().delete()
        SkillKnowledgeItem.objects.all().delete()
        SkillBehaviorIndicator.objects.all().delete()
        CareerStage.objects.all().delete()
        CareerPath.objects.all().delete()
        JobRole.objects.all().delete()
        JobFamily.objects.all().delete()
        Skill.objects.all().delete()
        Competency.objects.all().delete()
        SkillDomain.objects.all().delete()

    def _create_skill_domains(self):
        """Create skill domains"""
        domains_data = [
            {"slug": "programming", "name": "Programming", "description": "Software development and coding skills"},
            {"slug": "database", "name": "Database", "description": "Database design and management"},
            {"slug": "frontend", "name": "Frontend", "description": "User interface and client-side development"},
            {"slug": "backend", "name": "Backend", "description": "Server-side development and APIs"},
            {"slug": "soft_skill", "name": "Soft Skills", "description": "Interpersonal and communication skills"},
            {"slug": "devops", "name": "DevOps", "description": "Infrastructure and deployment"},
        ]

        domains = []
        for data in domains_data:
            domain, created = SkillDomain.objects.get_or_create(slug=data["slug"], defaults=data)
            domains.append(domain)
        return domains

    def _create_skills(self, domains):
        """Create skills"""
        domain_map = {d.slug: d for d in domains}

        skills_data = [
            {"slug": "python", "name": "Python", "domain": domain_map["programming"], "technologies": "Python, Django, Flask"},
            {"slug": "javascript", "name": "JavaScript", "domain": domain_map["programming"], "technologies": "JavaScript, Node.js, Express"},
            {"slug": "sql", "name": "SQL", "domain": domain_map["database"], "technologies": "PostgreSQL, MySQL, SQLite"},
            {"slug": "react", "name": "React", "domain": domain_map["frontend"], "technologies": "React, Redux, Next.js"},
            {"slug": "rest_api", "name": "REST API", "domain": domain_map["backend"], "technologies": "REST, GraphQL, FastAPI"},
            {"slug": "teamwork", "name": "Teamwork", "domain": domain_map["soft_skill"], "technologies": ""},
            {"slug": "docker", "name": "Docker", "domain": domain_map["devops"], "technologies": "Docker, Kubernetes, CI/CD"},
        ]

        skills = []
        for data in skills_data:
            skill, created = Skill.objects.get_or_create(slug=data["slug"], defaults=data)
            skills.append(skill)
        return skills

    def _create_competencies(self):
        """Create competencies"""
        competencies_data = [
            {
                "slug": "python_programming",
                "name": "Python Programming",
                "type": Competency.Type.TECHNICAL,
                "description": "Ability to write and maintain Python applications",
                "technologies": "Python, Django, Flask, FastAPI",
            },
            {
                "slug": "database_design",
                "name": "Database Design",
                "type": Competency.Type.TECHNICAL,
                "description": "Design and implement database schemas",
                "technologies": "PostgreSQL, MySQL, MongoDB",
            },
            {
                "slug": "frontend_development",
                "name": "Frontend Development",
                "type": Competency.Type.TECHNICAL,
                "description": "Build user interfaces and client-side applications",
                "technologies": "React, Vue, Angular, TypeScript",
            },
            {
                "slug": "api_design",
                "name": "API Design",
                "type": Competency.Type.TECHNICAL,
                "description": "Design and implement RESTful APIs",
                "technologies": "REST, GraphQL, OpenAPI",
            },
            {
                "slug": "collaboration",
                "name": "Collaboration",
                "type": Competency.Type.BEHAVIORAL,
                "description": "Work effectively in teams",
                "technologies": "",
            },
        ]

        competencies = []
        for data in competencies_data:
            competency, created = Competency.objects.get_or_create(slug=data["slug"], defaults=data)
            competencies.append(competency)
        return competencies

    def _create_competency_skills(self, competencies, skills):
        """Link skills to competencies"""
        competency_map = {c.slug: c for c in competencies}
        skill_map = {s.slug: s for s in skills}

        links = [
            {"competency": competency_map["python_programming"], "skill": skill_map["python"], "weight": 90},
            {"competency": competency_map["database_design"], "skill": skill_map["sql"], "weight": 85},
            {"competency": competency_map["frontend_development"], "skill": skill_map["react"], "weight": 80},
            {"competency": competency_map["frontend_development"], "skill": skill_map["javascript"], "weight": 70},
            {"competency": competency_map["api_design"], "skill": skill_map["rest_api"], "weight": 90},
            {"competency": competency_map["api_design"], "skill": skill_map["python"], "weight": 60},
            {"competency": competency_map["collaboration"], "skill": skill_map["teamwork"], "weight": 100},
        ]

        competency_skills = []
        for link in links:
            cs, created = CompetencySkill.objects.get_or_create(
                competency=link["competency"], skill=link["skill"], defaults={"weight": link["weight"]}
            )
            competency_skills.append(cs)
        return competency_skills

    def _create_job_families(self):
        """Create job families"""
        families_data = [
            {"slug": "engineering", "name": "Engineering", "description": "Software engineering roles"},
            {"slug": "product", "name": "Product", "description": "Product management roles"},
            {"slug": "design", "name": "Design", "description": "Design and UX roles"},
        ]

        families = []
        for data in families_data:
            family, created = JobFamily.objects.get_or_create(slug=data["slug"], defaults=data)
            families.append(family)
        return families

    def _create_job_roles(self, job_families):
        """Create job roles"""
        family_map = {f.slug: f for f in job_families}

        roles_data = [
            {
                "slug": "backend_developer",
                "name": "Backend Developer",
                "job_family": family_map["engineering"],
                "description": "Develops server-side applications and APIs",
            },
            {
                "slug": "frontend_developer",
                "name": "Frontend Developer",
                "job_family": family_map["engineering"],
                "description": "Develops user interfaces and client-side applications",
            },
            {
                "slug": "fullstack_developer",
                "name": "Full Stack Developer",
                "job_family": family_map["engineering"],
                "description": "Develops both frontend and backend applications",
            },
        ]

        roles = []
        for data in roles_data:
            role, created = JobRole.objects.get_or_create(slug=data["slug"], defaults=data)
            roles.append(role)
        return roles

    def _create_career_paths(self, job_roles):
        """Create career paths"""
        role_map = {r.slug: r for r in job_roles}

        paths_data = [
            {
                "name": "Backend Development Track",
                "job_role": role_map["backend_developer"],
                "description": "Career progression for backend developers",
            },
            {
                "name": "Frontend Development Track",
                "job_role": role_map["frontend_developer"],
                "description": "Career progression for frontend developers",
            },
        ]

        paths = []
        for data in paths_data:
            path, created = CareerPath.objects.get_or_create(
                job_role=data["job_role"], name=data["name"], defaults=data
            )
            paths.append(path)
        return paths

    def _create_career_stages(self, career_paths):
        """Create career stages"""
        stages_data = []
        for path in career_paths:
            stages_data.extend(
                [
                    {
                        "career_path": path,
                        "sequence": 1,
                        "title": f"Junior {path.job_role.name}",
                        "goal": f"Entry-level position for {path.job_role.name.lower()}",
                    },
                    {
                        "career_path": path,
                        "sequence": 2,
                        "title": f"Mid-level {path.job_role.name}",
                        "goal": f"Intermediate position for {path.job_role.name.lower()}",
                    },
                    {
                        "career_path": path,
                        "sequence": 3,
                        "title": f"Senior {path.job_role.name}",
                        "goal": f"Advanced position for {path.job_role.name.lower()}",
                    },
                ]
            )

        stages = []
        for data in stages_data:
            stage, created = CareerStage.objects.get_or_create(
                career_path=data["career_path"],
                sequence=data["sequence"],
                defaults={"title": data["title"], "goal": data["goal"]},
            )
            stages.append(stage)
        return stages

    def _create_stage_competencies(self, career_stages, competencies):
        """Link competencies to career stages"""
        competency_map = {c.slug: c for c in competencies}

        # Group stages by path
        stages_by_path = {}
        for stage in career_stages:
            if stage.career_path not in stages_by_path:
                stages_by_path[stage.career_path] = []
            stages_by_path[stage.career_path].append(stage)

        links = []
        for path, stages in stages_by_path.items():
            # Junior stage gets foundation level
            if len(stages) > 0:
                links.append(
                    {
                        "stage": stages[0],
                        "competency": competency_map["collaboration"],
                        "required_level": StageCompetency.RequiredLevel.FOUNDATION,
                    }
                )

            # Mid-level gets core competencies
            if len(stages) > 1:
                if "backend" in path.job_role.slug:
                    links.append(
                        {
                            "stage": stages[1],
                            "competency": competency_map["python_programming"],
                            "required_level": StageCompetency.RequiredLevel.CORE,
                        }
                    )
                    links.append(
                        {
                            "stage": stages[1],
                            "competency": competency_map["api_design"],
                            "required_level": StageCompetency.RequiredLevel.CORE,
                        }
                    )
                elif "frontend" in path.job_role.slug:
                    links.append(
                        {
                            "stage": stages[1],
                            "competency": competency_map["frontend_development"],
                            "required_level": StageCompetency.RequiredLevel.CORE,
                        }
                    )

            # Senior gets applied level
            if len(stages) > 2:
                if "backend" in path.job_role.slug:
                    links.append(
                        {
                            "stage": stages[2],
                            "competency": competency_map["database_design"],
                            "required_level": StageCompetency.RequiredLevel.APPLIED,
                        }
                    )

        stage_competencies = []
        for link in links:
            sc, created = StageCompetency.objects.get_or_create(
                stage=link["stage"],
                competency=link["competency"],
                defaults={"required_level": link["required_level"]},
            )
            stage_competencies.append(sc)
        return stage_competencies

    def _create_skill_behavior_indicators(self, skills):
        """Create skill behavior indicators"""
        skill_map = {s.slug: s for s in skills}
        indicators = []

        # Add indicators for Python skill
        if "python" in skill_map:
            python_skill = skill_map["python"]
            indicators_data = [
                {
                    "skill": python_skill,
                    "level": SkillBehaviorIndicator.Level.FOUNDATION,
                    "description": "Can write basic Python scripts and understand syntax",
                },
                {
                    "skill": python_skill,
                    "level": SkillBehaviorIndicator.Level.CORE,
                    "description": "Can build applications using frameworks like Django or Flask",
                },
                {
                    "skill": python_skill,
                    "level": SkillBehaviorIndicator.Level.APPLIED,
                    "description": "Can architect complex systems and mentor others",
                },
            ]
            for data in indicators_data:
                indicator, created = SkillBehaviorIndicator.objects.get_or_create(
                    skill=data["skill"], level=data["level"], defaults={"description": data["description"]}
                )
                indicators.append(indicator)

        return indicators

    def _create_skill_knowledge_items(self, skills):
        """Create skill knowledge items"""
        skill_map = {s.slug: s for s in skills}
        items = []

        if "python" in skill_map:
            python_skill = skill_map["python"]
            items_data = [
                {
                    "skill": python_skill,
                    "description": "Understanding of Python data structures (lists, dicts, sets)",
                },
                {
                    "skill": python_skill,
                    "description": "Knowledge of object-oriented programming in Python",
                },
            ]
            for data in items_data:
                item, created = SkillKnowledgeItem.objects.get_or_create(
                    skill=data["skill"], description=data["description"]
                )
                items.append(item)

        return items

    def _create_skill_attitude_tags(self, skills):
        """Create skill attitude tags"""
        skill_map = {s.slug: s for s in skills}
        tags = []

        if "python" in skill_map:
            python_skill = skill_map["python"]
            tags_data = [
                {"skill": python_skill, "tag": "Attention to Detail", "description": "Focuses on code quality"},
                {"skill": python_skill, "tag": "Continuous Learning", "description": "Keeps up with Python ecosystem"},
            ]
            for data in tags_data:
                tag, created = SkillAttitudeTag.objects.get_or_create(
                    skill=data["skill"], tag=data["tag"], defaults={"description": data.get("description", "")}
                )
                tags.append(tag)

        return tags

