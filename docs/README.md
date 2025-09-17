# BreatheCode API v2

A comprehensive Django-based API for managing educational technology platforms, built with modern Python practices and designed for scalability.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Apps](#core-apps)
- [Support Services](#support-services)
- [Key Dependencies](#key-dependencies)
- [Best Practices](#best-practices)
- [Development Guidelines](#development-guidelines)
- [API Structure](#api-structure)
- [Security](#security)
- [Testing](#testing)
- [Deployment](#deployment)

## Overview

The BreatheCode API is a Django-based platform that provides comprehensive functionality for educational technology companies. It manages students, courses, payments, mentorship, events, and more through a modular architecture built with Django apps.

**Key Features:**
- Multi-tenant academy management
- Student lifecycle management
- Payment processing and subscriptions
- Mentorship and event coordination
- Comprehensive monitoring and analytics
- Multi-language support
- Asynchronous task processing

## Architecture

The API follows Django's MVT (Model-View-Template) pattern with a REST API focus. It's built around the concept of **Academies** as the main organizational unit, with all other entities being scoped to specific academies.

### Core Principles
- **Multi-tenancy**: Each academy operates independently
- **Modularity**: Functionality is separated into focused Django apps
- **Scalability**: Async support, background tasks, and efficient database design
- **Security**: Comprehensive authentication, authorization, and data validation
- **Internationalization**: Multi-language support throughout the system

## Core Apps

### 1. **admissions** - Student & Academy Management
**Purpose**: Core student lifecycle management and academy configuration

**Key Models**:
- `Academy`: Multi-tenant organization unit
- `Cohort`: Group of students learning together
- `Syllabus`: Course curriculum and structure
- `CohortUser`: Student enrollment in cohorts
- `Country/City`: Geographic data for academies

**Best Practices**:
- Use `Academy` as the primary scope for all operations
- Implement proper cohort lifecycle management
- Use signals for enrollment state changes
- Validate geographic data integrity

**Interconnections**:
- Referenced by: payments, events, mentorship, assignments
- Provides: User context, academy settings, geographic data

### 2. **authenticate** - User Management & Authentication
**Purpose**: User authentication, authorization, and profile management

**Key Models**:
- `User`: Extended Django user model
- `Profile`: User profile information
- `Role`: User roles and permissions
- `Capability`: Granular permissions
- `Token`: Authentication tokens (login, one-time, temporal)

**Best Practices**:
- Use Django's built-in authentication system
- Implement proper token lifecycle management
- Use signals for user state changes
- Implement proper permission checking

**Interconnections**:
- Referenced by: All other apps
- Provides: User authentication, authorization, profiles

### 3. **payments** - Financial Management
**Purpose**: Payment processing, subscriptions, and financial tracking

**Key Models**:
- `Service`: Sellable services (cohorts, mentorship, events)
- `Plan`: Subscription plans with pricing
- `Bag`: Shopping cart and checkout process
- `Subscription`: Recurring payment management
- `PlanFinancing`: Installment-based payments
- `Consumable`: Service usage tracking
- `Invoice`: Payment records and status

**Best Practices**:
- Never store credit card information
- Use proper validation for financial transactions
- Implement comprehensive error handling
- Use signals for payment state changes
- Track all financial activities for audit

**Interconnections**:
- References: admissions (academies, cohorts), authenticate (users)
- Provides: Payment processing for all services

### 4. **mentorship** - Mentorship Services
**Purpose**: Managing mentorship sessions and mentor-mentee relationships

**Key Models**:
- `MentorshipService`: Configurable mentorship offerings
- `MentorshipSession`: Individual mentorship meetings
- `Mentor`: Qualified mentors
- `Mentee`: Students receiving mentorship
- `AcademyMentorshipSettings`: Academy-specific configuration

**Best Practices**:
- Use proper session scheduling and management
- Implement video provider integration
- Handle missed sessions appropriately
- Use signals for session state changes

**Interconnections**:
- References: admissions (academies, cohorts), authenticate (users)
- Provides: Mentorship services for students

### 5. **events** - Event Management
**Purpose**: Managing events, workshops, and live classes

**Key Models**:
- `Event`: Individual events and workshops
- `EventType`: Categorization of events
- `EventCheckin`: Attendance tracking
- `Venue`: Physical and virtual locations
- `Organization`: Event organization management

**Best Practices**:
- Implement proper event lifecycle management
- Use signals for attendance tracking
- Handle venue management efficiently
- Support both physical and virtual events

**Interconnections**:
- References: admissions (academies, cohorts), authenticate (users)
- Provides: Event services for students

### 6. **assignments** - Academic Work Management
**Purpose**: Managing student assignments, projects, and assessments

**Key Models**:
- `Assignment`: Individual assignments
- `Task`: Specific tasks within assignments
- `AssignmentSubmission`: Student work submissions
- `Grading`: Assessment and feedback

**Best Practices**:
- Implement proper assignment lifecycle
- Use signals for submission tracking
- Handle file uploads securely
- Implement proper grading workflows

**Interconnections**:
- References: admissions (cohorts), authenticate (users)
- Provides: Academic work management

### 7. **assessment** - Evaluation & Testing
**Purpose**: Managing quizzes, tests, and evaluations

**Key Models**:
- `Assessment`: Tests and evaluations
- `Question`: Individual test questions
- `Answer`: Student responses
- `Score`: Assessment results

**Best Practices**:
- Implement secure test delivery
- Use proper randomization for questions
- Handle time limits appropriately
- Implement comprehensive scoring

**Interconnections**:
- References: admissions (cohorts), authenticate (users)
- Provides: Assessment services

### 8. **certificate** - Achievement Recognition
**Purpose**: Managing student certificates and achievements

**Key Models**:
- `Certificate`: Student achievement records
- `CertificateTemplate`: Certificate design templates
- `CertificateGeneration`: Certificate creation process

**Best Practices**:
- Implement secure certificate generation
- Use proper template management
- Handle certificate verification
- Implement proper achievement tracking

**Interconnections**:
- References: admissions (cohorts), authenticate (users)
- Provides: Achievement recognition

### 9. **marketing** - Marketing & Communication
**Purpose**: Managing marketing campaigns and communications

**Key Models**:
- `Campaign`: Marketing campaigns
- `Lead`: Potential student information
- `FormSubmission`: Lead capture forms
- `EmailTemplate`: Communication templates

**Best Practices**:
- Implement proper lead management
- Use signals for campaign tracking
- Handle GDPR compliance
- Implement proper email management

**Interconnections**:
- References: admissions (academies), authenticate (users)
- Provides: Marketing services

### 11. **feedback** - User Feedback & Reviews
**Purpose**: Collecting and managing user feedback

**Key Models**:
- `Feedback`: User feedback records
- `Review`: Detailed reviews
- `Rating`: Numerical ratings

**Best Practices**:
- Implement proper feedback collection
- Use signals for feedback processing
- Handle anonymous feedback appropriately
- Implement proper moderation workflows

**Interconnections**:
- References: admissions (academies), authenticate (users)
- Provides: Feedback collection services

### 12. **media** - File & Asset Management
**Purpose**: Managing files, images, and media assets

**Key Models**:
- `Media`: File and asset records
- `MediaCategory`: Asset categorization
- `MediaTag`: Asset tagging system

**Best Practices**:
- Implement secure file uploads
- Use proper file validation
- Handle file storage efficiently
- Implement proper access control

**Interconnections**:
- References: admissions (academies), authenticate (users)
- Provides: Media management for all apps

### 13. **registry** - Asset & Content Management
**Purpose**: Managing educational content and assets

**Key Models**:
- `Asset`: Educational content items
- `AssetCategory`: Content categorization
- `AssetTag`: Content tagging

**Best Practices**:
- Implement proper content lifecycle
- Use signals for content changes
- Handle content versioning
- Implement proper access control

**Interconnections**:
- References: admissions (academies), authenticate (users)
- Provides: Content management for all apps

### 14. **monitoring** - System Health & Performance
**Purpose**: Monitoring system health and performance

**Key Models**:
- `Application`: Monitored applications
- `Endpoint`: API endpoint monitoring
- `MonitorScript`: Custom monitoring scripts
- `Supervisor`: Automated issue detection and resolution

**Best Practices**:
- Implement comprehensive monitoring
- Use supervisors for automated fixes
- Handle alerts appropriately
- Implement proper escalation

**Interconnections**:
- References: All other apps
- Provides: System monitoring and health

### 15. **notify** - Communication & Notifications
**Purpose**: Managing notifications and communications

**Key Models**:
- `Notification`: User notifications
- `SlackChannel`: Slack integration
- `EmailTemplate`: Email templates
- `SMS`: SMS messaging

**Best Practices**:
- Implement proper notification delivery
- Use signals for notification triggers
- Handle delivery failures
- Implement proper rate limiting

**Interconnections**:
- References: All other apps
- Provides: Communication services

### 16. **provisioning** - Resource Provisioning
**Purpose**: Managing resource allocation and provisioning

**Key Models**:
- `Provisioning`: Resource provisioning records
- `Resource`: Available resources
- `Allocation`: Resource assignments

**Best Practices**:
- Implement proper resource lifecycle
- Use signals for allocation changes
- Handle resource conflicts
- Implement proper cleanup

**Interconnections**:
- References: admissions (academies), authenticate (users)
- Provides: Resource management services

### 17. **commission** - Commission & Referral Management
**Purpose**: Managing commissions and referral programs

**Key Models**:
- `Commission`: Commission records
- `Referral`: Referral tracking
- `Payout`: Commission payouts

**Best Practices**:
- Implement proper commission calculation
- Use signals for referral tracking
- Handle payout processing
- Implement proper audit trails

**Interconnections**:
- References: payments, authenticate (users)
- Provides: Commission management services

### 18. **activity** - User Activity Tracking
**Purpose**: Tracking user activity and engagement

**Key Models**:
- `StudentActivity`: Student activity records
- `ActivityType`: Types of activities
- `ActivityMetric`: Activity measurements

**Best Practices**:
- Implement efficient activity tracking
- Use BigQuery for analytics
- Handle data privacy appropriately
- Implement proper data retention

**Interconnections**:
- References: All other apps
- Provides: Activity analytics and insights

## Support Services

### **utils** - Shared Utilities
**Purpose**: Common utilities and helper functions used across apps

**Key Features**:
- Database utilities
- Validation helpers
- URL utilities
- View utilities
- Pagination helpers

**Best Practices**:
- Keep utilities generic and reusable
- Implement proper error handling
- Use type hints for clarity
- Document complex functions

### **services** - External Service Integrations
**Purpose**: Third-party service integrations and APIs

**Key Features**:
- Payment processor integrations
- Email service providers
- SMS services
- File storage services
- Analytics services

**Best Practices**:
- Implement proper error handling
- Use circuit breakers for reliability
- Implement proper retry logic
- Handle rate limiting appropriately

### **static** - Static File Management
**Purpose**: Static file serving and management

**Key Features**:
- CSS, JavaScript, and image files
- Static file optimization
- CDN integration

**Best Practices**:
- Optimize static files for performance
- Use proper caching headers
- Implement CDN integration
- Handle file versioning

### **tests** - Testing Infrastructure
**Purpose**: Testing utilities and shared test code

**Key Features**:
- Test fixtures
- Test utilities
- Common test setup
- Mock data generators

**Best Practices**:
- Keep tests focused and isolated
- Use proper test data management
- Implement comprehensive coverage
- Use proper test naming conventions

## Key Dependencies

### Core Framework
- **Django 5.1+**: Modern Django with async support
- **Django REST Framework**: REST API framework
- **ADRF**: Async Django REST Framework for async views

### 4Geeks Libraries
- **capy-core**: Core utilities and serializers
- **celery-task-manager**: Background task management
- **linked-services**: Service integration framework

### Database & Caching
- **PostgreSQL**: Primary database
- **Redis**: Caching and session storage
- **BigQuery**: Analytics and reporting

### Background Tasks
- **Celery**: Asynchronous task processing
- **RabbitMQ**: Message queue for tasks

### External Services
- **Stripe**: Payment processing
- **Google Cloud**: Storage, analytics, and services
- **Slack**: Communication integration
- **Eventbrite**: Event management

### Development & Testing
- **Poetry**: Dependency management
- **Pytest**: Testing framework
- **Black**: Code formatting
- **Flake8**: Code linting

## Best Practices

### 1. **Error Handling**
- Use `ValidationException` and `PaymentException` from Capy Core
- Implement proper error logging
- Return appropriate HTTP status codes
- Use translation for error messages

### 2. **Data Validation**
- Use Django model validation
- Implement custom validators when needed
- Use signals for complex validation
- Validate data at all trust boundaries

### 3. **Security**
- Implement proper authentication and authorization
- Use Django's built-in security features
- Validate all user inputs
- Implement proper CSRF protection

### 4. **Performance**
- Use database indexes appropriately
- Implement caching where beneficial
- Use async views for I/O-bound operations
- Optimize database queries

### 5. **Internationalization**
- Use translation functions throughout
- Support multiple languages
- Handle locale-specific formatting
- Implement proper text direction support

### 6. **Monitoring**
- Use supervisors for automated issue detection
- Implement comprehensive logging
- Monitor system health and performance
- Use proper alerting and escalation

## Development Guidelines

### 1. **Code Organization**
- Follow Django app structure
- Use meaningful model names
- Implement proper URL routing
- Use signals for decoupled communication

### 2. **Database Design**
- Use proper relationships and constraints
- Implement proper indexing
- Use migrations for schema changes
- Handle data integrity properly

### 3. **API Design**
- Use RESTful principles
- Implement proper versioning
- Use consistent naming conventions
- Implement proper pagination

### 4. **Testing**
- Write comprehensive tests
- Use proper test data management
- Test both success and failure cases
- Implement proper test isolation

### 5. **Documentation**
- Document complex functions
- Use proper docstrings
- Maintain up-to-date API documentation
- Document business logic and workflows

## API Structure

### URL Patterns
The API uses versioned URLs with clear namespace separation:

```
/v1/auth/          - Authentication endpoints
/v1/admissions/    - Student and academy management
/v1/payments/      - Financial operations
/v1/events/        - Event management
/v1/mentorship/    - Mentorship services
/v1/assignments/   - Academic work management
/v1/assessment/    - Testing and evaluation
/v1/certificate/   - Achievement recognition
/v1/marketing/     - Marketing operations
/v1/freelance/     - Freelance project management
/v1/feedback/      - User feedback collection
/v1/media/         - File and asset management
/v1/registry/      - Content management
/v1/monitoring/    - System health monitoring
/v1/notify/        - Communication services
/v1/provisioning/  - Resource management
/v1/commission/    - Commission tracking
/v1/activity/      - User activity analytics
```

### Authentication
- Token-based authentication
- Multiple token types (login, one-time, temporal, permanent)
- Role-based access control
- Granular permissions system

### Data Flow
1. **Request Processing**: Authentication and authorization
2. **Business Logic**: App-specific operations
3. **Data Persistence**: Database operations with validation
4. **Response Generation**: Formatted API responses
5. **Side Effects**: Signals, notifications, and background tasks

## Security

### Authentication & Authorization
- Multi-factor authentication support
- Role-based access control
- Granular permissions system
- Token lifecycle management

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection

### API Security
- Rate limiting
- Request validation
- Proper error handling
- Audit logging

## Testing

### Test Types
- **Unit Tests**: Individual component testing
- **Integration Tests**: App interaction testing
- **API Tests**: Endpoint functionality testing
- **Performance Tests**: Load and stress testing

### Test Tools
- **Pytest**: Primary testing framework
- **Pytest-Django**: Django integration
- **Pytest-Cov**: Coverage reporting
- **Pytest-Xdist**: Parallel test execution

### Test Data
- **Fixtures**: Predefined test data
- **Factories**: Dynamic test data generation
- **Mixers**: Model instance creation
- **Capy Core Fixtures**: Enhanced testing utilities

## Deployment

### Environment Configuration
- Environment-specific settings
- Secure configuration management
- Database connection handling
- External service configuration

### Performance Optimization
- Database optimization
- Caching strategies
- Static file optimization
- CDN integration

### Monitoring & Maintenance
- Health checks and monitoring
- Automated issue resolution
- Performance metrics
- Error tracking and alerting

## Getting Started

### Prerequisites
- Python 3.13+
- PostgreSQL 12+
- Redis 6+
- RabbitMQ 3.8+

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd apiv2

# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
poetry run migrate

# Start the development server
poetry run dev
```

### Development Commands
```bash
# Run tests
poetry run test

# Run tests with coverage
poetry run test:coverage

# Format code
poetry run format

# Lint code
poetry run lint

# Run migrations
poetry run migrate

# Create migrations
poetry run makemigrations
```

## Contributing

### Development Workflow
1. Create a feature branch
2. Implement changes with tests
3. Ensure code quality (linting, formatting)
4. Submit a pull request
5. Code review and approval
6. Merge and deploy

### Code Standards
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write comprehensive tests
- Document complex logic
- Use meaningful commit messages

## Support & Documentation

### Additional Resources
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Capy Core Documentation](https://breatheco-de.github.io/capy-core/)
- [Celery Task Manager](https://breatheco-de.github.io/celery-task-manager-django-plugin/)

### Getting Help
- Check existing documentation
- Review code examples
- Consult the development team
- Submit issues for bugs or feature requests

---

This API is designed to be scalable, maintainable, and secure. Follow the established patterns and best practices to ensure consistency and reliability across the platform.
