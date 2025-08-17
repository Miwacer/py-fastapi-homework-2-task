from pydantic import BaseModel, Field, field_validator
from datetime import date, timedelta
from typing import Literal


class MovieForList(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str

    class Config:
        from_attributes = True


class MovieListResponse(BaseModel):
    movies: list[MovieForList]
    prev_page: str | None
    next_page: str | None
    total_pages: int
    total_items: int

    class Config:
        from_attributes = True


class MovieCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    date: date
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: Literal["Released", "Post Production", "In Production"]
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: str
    genres: list[str]
    actors: list[str]
    languages: list[str]

    @field_validator("date")
    def date_not_too_far(cls, v):
        if v > date.today() + timedelta(days=365):
            raise ValueError("Date must not be more than one year in the future")
        return v


class CountryRead(BaseModel):
    id: int
    code: str
    name: str | None

    class Config:
        from_attributes = True


class GenresRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ActorsRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class LanguagesRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class MovieCreateResponse(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str
    status: str
    budget: float
    revenue: float
    country: CountryRead
    genres: list[GenresRead]
    actors: list[ActorsRead]
    languages: list[LanguagesRead]

    class Config:
        from_attributes = True


class MovieDetailResponse(MovieCreateResponse):
    pass


class MovieUpdateRequest(BaseModel):
    name: str = Field(None, min_length=1, max_length=255)
    date: date | None
    score: float = Field(None, ge=0, le=100)
    overview: str | None
    status: Literal["Released", "Post Production", "In Production"]
    budget: float = Field(None, ge=0)
    revenue: float = Field(None, ge=0)