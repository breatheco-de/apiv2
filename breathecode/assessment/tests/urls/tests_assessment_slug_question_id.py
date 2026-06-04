"""
Test cases for POST and PUT /v1/assessment/<assessment_slug>/question/<question_id>
"""

from rest_framework import status


def test_post_without_auth(client):
    """Test POST without authentication"""
    url = "/v1/assessment/test-assessment/question/1/option"
    response = client.post(url, {"title": "New option", "score": 1.0}, content_type="application/json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_post_without_capability(client, database):
    """Test POST without crud_assessment capability"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    
    database.create(capability={"slug": "read_assessment"})
    database.create(role={"slug": "reader", "name": "Reader"})
    
    role = Role.objects.get(slug="reader")
    capability = Capability.objects.get(slug="read_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)

    url = "/v1/assessment/test-assessment/question/1/option"
    client.force_authenticate(user=model.user)
    
    response = client.post(url, {"title": "New option", "score": 1.0}, format="json", HTTP_ACADEMY=model.academy.id)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_post_assessment_not_found(client, database):
    """Test POST with non-existent assessment"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    url = "/v1/assessment/non-existent/question/1/option"
    client.force_authenticate(user=model.user)
    
    response = client.post(url, {"title": "New option", "score": 1.0}, format="json", HTTP_ACADEMY=model.academy.id)
    data = response.json()

    assert response.status_code == 400
    assert "slug" in data or "detail" in data


def test_post_question_not_found(client, database):
    """Test POST with non-existent question"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    url = f"/v1/assessment/{assessment.slug}/question/999/option"
    client.force_authenticate(user=model.user)
    
    response = client.post(url, {"title": "New option", "score": 1.0}, format="json", HTTP_ACADEMY=model.academy.id)
    data = response.json()

    assert response.status_code == 400
    assert "slug" in data or "detail" in data


def test_post_create_new_option(client, database):
    """Test POST to create a new option for a question"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment, Question, Option
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment with question and one option
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    question = Question.objects.create(
        title="Test question",
        assessment=assessment,
        question_type="SELECT"
    )
    
    # Create initial option
    Option.objects.create(title="Existing Option", question=question, score=1.0)
    
    url = f"/v1/assessment/{assessment.slug}/question/{question.id}/option"
    client.force_authenticate(user=model.user)
    
    response = client.post(
        url,
        {
            "title": "New Option",
            "score": 0.0,
            "position": 2
        },
        format="json",
        HTTP_ACADEMY=model.academy.id
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    
    # Verify option was created
    assert data["title"] == "New Option"
    assert data["score"] == 0.0
    assert data["position"] == 2
    
    # Verify it's in the database
    assert Option.objects.filter(question=question).count() == 2
    new_option = Option.objects.get(question=question, title="New Option")
    assert new_option.score == 0.0


def test_post_invalid_option_data(client, database):
    """Test POST with invalid option data"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment, Question
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment with question
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    question = Question.objects.create(
        title="Test question",
        assessment=assessment,
        question_type="SELECT"
    )
    
    url = f"/v1/assessment/{assessment.slug}/question/{question.id}/option"
    client.force_authenticate(user=model.user)
    
    # Try to create option without required fields
    response = client.post(
        url,
        {"title": "New Option"},  # Missing score
        format="json",
        HTTP_ACADEMY=model.academy.id
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_with_help_text(client, database):
    """Test POST creating option with help_text"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment, Question, Option
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment with question
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    question = Question.objects.create(
        title="Test question",
        assessment=assessment,
        question_type="SELECT"
    )
    
    Option.objects.create(title="Existing", question=question, score=1.0)
    
    url = f"/v1/assessment/{assessment.slug}/question/{question.id}/option"
    client.force_authenticate(user=model.user)
    
    response = client.post(
        url,
        {
            "title": "Option with help",
            "help_text": "This is a hint",
            "score": 0.0,
            "position": 3
        },
        format="json",
        HTTP_ACADEMY=model.academy.id
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    
    assert data["title"] == "Option with help"
    assert data["help_text"] == "This is a hint"
    assert data["score"] == 0.0


def test_put_without_auth(client):
    """Test PUT without authentication"""
    url = "/v1/assessment/test-assessment/question/1"
    response = client.put(url, {"title": "Updated question"}, content_type="application/json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_put_without_capability(client, database):
    """Test PUT without crud_assessment capability"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    
    database.create(capability={"slug": "read_assessment"})
    database.create(role={"slug": "reader", "name": "Reader"})
    
    role = Role.objects.get(slug="reader")
    capability = Capability.objects.get(slug="read_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)

    url = "/v1/assessment/test-assessment/question/1"
    client.force_authenticate(user=model.user)
    
    response = client.put(url, {"title": "Updated question"}, format="json", HTTP_ACADEMY=model.academy.id)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_put_assessment_not_found(client, database):
    """Test PUT with non-existent assessment"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    url = "/v1/assessment/non-existent/question/1"
    client.force_authenticate(user=model.user)
    
    response = client.put(url, {"title": "Updated question"}, format="json", HTTP_ACADEMY=model.academy.id)
    data = response.json()

    assert response.status_code == 400
    assert "slug" in data or "detail" in data


def test_put_question_not_found(client, database):
    """Test PUT with non-existent question"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    url = f"/v1/assessment/{assessment.slug}/question/999"
    client.force_authenticate(user=model.user)
    
    response = client.put(url, {"title": "Updated question"}, format="json", HTTP_ACADEMY=model.academy.id)
    data = response.json()

    assert response.status_code == 400
    assert "slug" in data or "detail" in data


def test_put_update_question_title_only(client, database):
    """Test PUT updating only question title"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment, Question, Option
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment with question and options
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    question = Question.objects.create(
        title="Original question",
        assessment=assessment,
        question_type="SELECT"
    )
    
    option1 = Option.objects.create(title="Option 1", question=question, score=1.0)
    option2 = Option.objects.create(title="Option 2", question=question, score=0.0)
    
    url = f"/v1/assessment/{assessment.slug}/question/{question.id}"
    client.force_authenticate(user=model.user)
    
    response = client.put(
        url,
        {"title": "Updated question title"},
        format="json",
        HTTP_ACADEMY=model.academy.id
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify question was updated
    question.refresh_from_db()
    assert question.title == "Updated question title"
    
    # Verify options weren't changed
    assert Option.objects.filter(question=question).count() == 2


def test_put_update_question_with_existing_options(client, database):
    """Test PUT updating question and its existing options"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment, Question, Option
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment with question and options
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    question = Question.objects.create(
        title="Original question",
        assessment=assessment,
        question_type="SELECT"
    )
    
    option1 = Option.objects.create(title="Option 1", question=question, score=1.0)
    option2 = Option.objects.create(title="Option 2", question=question, score=0.0)
    
    url = f"/v1/assessment/{assessment.slug}/question/{question.id}"
    client.force_authenticate(user=model.user)
    
    response = client.put(
        url,
        {
            "title": "Updated question",
            "options": [
                {"id": option1.id, "title": "Updated Option 1", "score": 0.5},
                {"id": option2.id, "title": "Updated Option 2", "score": 0.5}
            ]
        },
        format="json",
        HTTP_ACADEMY=model.academy.id
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify question was updated
    question.refresh_from_db()
    assert question.title == "Updated question"
    
    # Verify options were updated
    option1.refresh_from_db()
    option2.refresh_from_db()
    assert option1.title == "Updated Option 1"
    assert option1.score == 0.5
    assert option2.title == "Updated Option 2"
    assert option2.score == 0.5


def test_put_add_new_options_to_question(client, database):
    """Test PUT adding new options to existing question"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment, Question, Option
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment with question and options
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    question = Question.objects.create(
        title="Original question",
        assessment=assessment,
        question_type="SELECT"
    )
    
    option1 = Option.objects.create(title="Option 1", question=question, score=1.0)
    
    url = f"/v1/assessment/{assessment.slug}/question/{question.id}"
    client.force_authenticate(user=model.user)
    
    response = client.put(
        url,
        {
            "title": "Updated question",
            "options": [
                {"id": option1.id, "title": "Option 1", "score": 1.0},
                {"title": "New Option 2", "score": 0.0},
                {"title": "New Option 3", "score": 0.0}
            ]
        },
        format="json",
        HTTP_ACADEMY=model.academy.id
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify new options were created
    assert Option.objects.filter(question=question).count() == 3
    
    new_option2 = Option.objects.get(question=question, title="New Option 2")
    assert new_option2.score == 0.0
    
    new_option3 = Option.objects.get(question=question, title="New Option 3")
    assert new_option3.score == 0.0


def test_put_invalid_total_score(client, database):
    """Test PUT with invalid total score (must be > 0)"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment, Question, Option
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment with question and options
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    question = Question.objects.create(
        title="Original question",
        assessment=assessment,
        question_type="SELECT"
    )
    
    option1 = Option.objects.create(title="Option 1", question=question, score=1.0)
    option2 = Option.objects.create(title="Option 2", question=question, score=0.0)
    
    url = f"/v1/assessment/{assessment.slug}/question/{question.id}"
    client.force_authenticate(user=model.user)
    
    # Try to update with all negative or zero scores
    response = client.put(
        url,
        {
            "title": "Updated question",
            "options": [
                {"id": option1.id, "title": "Option 1", "score": 0.0},
                {"id": option2.id, "title": "Option 2", "score": 0.0}
            ]
        },
        format="json",
        HTTP_ACADEMY=model.academy.id
    )
    
    data = response.json()
    
    assert response.status_code == 400
    assert "slug" in data or "detail" in data


def test_put_option_not_found(client, database):
    """Test PUT with invalid option ID"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment, Question, Option
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment with question and options
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    question = Question.objects.create(
        title="Original question",
        assessment=assessment,
        question_type="SELECT"
    )
    
    option1 = Option.objects.create(title="Option 1", question=question, score=1.0)
    
    url = f"/v1/assessment/{assessment.slug}/question/{question.id}"
    client.force_authenticate(user=model.user)
    
    response = client.put(
        url,
        {
            "title": "Updated question",
            "options": [
                {"id": 999, "title": "Non-existent option", "score": 1.0}
            ]
        },
        format="json",
        HTTP_ACADEMY=model.academy.id
    )
    
    data = response.json()
    
    assert response.status_code == 400
    assert "slug" in data or "detail" in data


def test_put_partial_update(client, database):
    """Test PUT with partial update (only some fields)"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment, Question, Option
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create assessment with question and options
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user
    )
    
    question = Question.objects.create(
        title="Original question",
        help_text="Original help text",
        assessment=assessment,
        question_type="SELECT"
    )
    
    option1 = Option.objects.create(title="Option 1", question=question, score=1.0)
    
    url = f"/v1/assessment/{assessment.slug}/question/{question.id}"
    client.force_authenticate(user=model.user)
    
    # Update only help_text, keep title unchanged
    response = client.put(
        url,
        {"help_text": "Updated help text"},
        format="json",
        HTTP_ACADEMY=model.academy.id
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    # Verify only help_text was updated
    question.refresh_from_db()
    assert question.help_text == "Updated help text"
    assert question.title == "Original question"


def test_put_archived_assessment(client, database):
    """Test PUT on archived assessment should fail"""
    from breathecode.authenticate.models import ProfileAcademy, Role, Capability
    from breathecode.assessment.models import Assessment, Question, Option
    
    database.create(capability={"slug": "crud_assessment"})
    database.create(role={"slug": "admin", "name": "Admin"})
    
    role = Role.objects.get(slug="admin")
    capability = Capability.objects.get(slug="crud_assessment")
    role.capabilities.set([capability])
    
    model = database.create(user=1, city=1, country=1, academy=1)
    ProfileAcademy.objects.create(user=model.user, academy=model.academy, role=role, email=model.user.email)
    
    # Create archived assessment with question
    assessment = Assessment.objects.create(
        slug="test-assessment",
        title="Test Assessment",
        academy=model.academy,
        author=model.user,
        is_archived=True
    )
    
    question = Question.objects.create(
        title="Original question",
        assessment=assessment,
        question_type="SELECT"
    )
    
    Option.objects.create(title="Option 1", question=question, score=1.0)
    
    url = f"/v1/assessment/{assessment.slug}/question/{question.id}"
    client.force_authenticate(user=model.user)
    
    response = client.put(
        url,
        {"title": "Updated question"},
        format="json",
        HTTP_ACADEMY=model.academy.id
    )
    
    data = response.json()
    
    assert response.status_code == 400
    assert "slug" in data or "detail" in data

