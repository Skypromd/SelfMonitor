import uuid

from pydantic import BaseModel


# This file is intended to hold Pydantic models that are shared across multiple services.
# For example, a User model that is used by both auth-service and user-profile-service.

class SharedUser(BaseModel):
    """
    A representation of a user that can be safely shared between services,
    excluding sensitive information like password hashes.
    """
    id: uuid.UUID
    email: str
    is_active: bool
