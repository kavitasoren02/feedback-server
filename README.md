# Feedback Management System API

A comprehensive FastAPI-based backend system for managing employee feedback with role-based access control.

## Features

### Core Features
- **Authentication & Authorization**: JWT-based auth with Manager/Employee roles
- **Feedback Management**: Create, read, update, delete feedback with proper permissions
- **Custom Forms**: Managers can create custom feedback forms
- **Dashboard Analytics**: Role-specific dashboards with insights
- **Team Management**: Managers can only see their team members

### API Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user info
- `GET /api/auth/team-members` - Get team members (managers only)

#### Feedback
- `POST /api/feedback/` - Create feedback (managers only)
- `GET /api/feedback/` - Get feedback (filtered by role)
- `GET /api/feedback/{id}` - Get specific feedback
- `PUT /api/feedback/{id}` - Update feedback (managers only)
- `POST /api/feedback/{id}/acknowledge` - Acknowledge feedback (employees only)
- `DELETE /api/feedback/{id}` - Delete feedback (managers only)

#### Dashboard
- `GET /api/dashboard/manager` - Manager dashboard
- `GET /api/dashboard/employee` - Employee dashboard
- `GET /api/dashboard/stats` - General stats

#### Forms
- `POST /api/forms/` - Create feedback form (managers only)
- `GET /api/forms/` - Get all forms
- `GET /api/forms/{id}` - Get specific form
- `PUT /api/forms/{id}` - Update form
- `DELETE /api/forms/{id}` - Delete form
- `GET /api/forms/active/list` - Get active forms

## Setup Instructions

### Prerequisites
- Python 3.11+
- MongoDB (local or Atlas)
- Docker (optional)

### Local Development

1. **Clone and setup**:
\`\`\`bash
git clone <repository>
cd feedback-backend
pip install -r requirements.txt
\`\`\`

2. **Environment setup**:
\`\`\`bash
cp .env.example .env
# Edit .env with your MongoDB URL and secret key
\`\`\`

3. **Run the application**:
\`\`\`bash
python main.py
\`\`\`

4. **Seed sample data**:
\`\`\`bash
python scripts/seed_data.py
\`\`\`

### Docker Setup

1. **Run with Docker Compose**:
\`\`\`bash
docker-compose up -d
\`\`\`

This will start both MongoDB and the API server.

### API Documentation

Once running, visit:
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Schema

### Users Collection
\`\`\`json
{
  "_id": "ObjectId",
  "email": "string",
  "password": "hashed_string",
  "full_name": "string",
  "role": "manager|employee",
  "employee_id": "string",
  "department": "string",
  "manager_id": "string",
  "created_at": "datetime",
  "is_active": "boolean"
}
\`\`\`

### Feedback Collection
\`\`\`json
{
  "_id": "ObjectId",
  "employee_id": "string",
  "manager_id": "string",
  "strengths": "string",
  "areas_to_improve": "string",
  "overall_sentiment": "positive|neutral|negative",
  "additional_notes": "string",
  "form_data": "object",
  "created_at": "datetime",
  "updated_at": "datetime",
  "is_acknowledged": "boolean",
  "acknowledged_at": "datetime"
}
\`\`\`

### Forms Collection
\`\`\`json
{
  "_id": "ObjectId",
  "title": "string",
  "description": "string",
  "manager_id": "string",
  "fields": [
    {
      "id": "string",
      "label": "string",
      "type": "text|textarea|select|rating|checkbox",
      "required": "boolean",
      "options": ["array"],
      "placeholder": "string"
    }
  ],
  "is_active": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
\`\`\`

## Sample Data

After running the seed script, you can use these credentials:

**Managers:**
- john.manager@company.com / password123
- sarah.lead@company.com / password123

**Employees:**
- alice.dev@company.com / password123
- bob.dev@company.com / password123
- carol.marketing@company.com / password123

## Security Features

- JWT token-based authentication
- Password hashing with bcrypt
- Role-based access control
- Input validation with Pydantic
- CORS protection
- Database indexes for performance

## Production Considerations

1. **Environment Variables**: Set proper values in production
2. **Database**: Use MongoDB Atlas or properly secured MongoDB
3. **CORS**: Configure allowed origins
4. **Rate Limiting**: Add rate limiting middleware
5. **Logging**: Implement proper logging
6. **Monitoring**: Add health checks and monitoring
7. **SSL**: Use HTTPS in production

## Testing

The API includes comprehensive error handling and validation. Test using the interactive docs at `/docs` or with tools like Postman.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper tests
4. Submit a pull request

## License

MIT License
