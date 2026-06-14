from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    sub: str | None = None

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)