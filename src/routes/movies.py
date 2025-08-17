from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status
)
from sqlalchemy import select, func, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas import (
    MovieListResponse,
    MovieCreateRequest,
    MovieCreateResponse,
    MovieDetailResponse,
    MovieUpdateResponse
)


router = APIRouter()


async def get_or_create_country(db: AsyncSession, country_code: str) -> CountryModel:
    result = await db.execute(
        select(CountryModel).where(CountryModel.code == country_code)
    )
    country = result.scalar_one_or_none()

    if country:
        return country

    new_country = CountryModel(code=country_code)
    db.add(new_country)

    try:
        await db.commit()
        await db.refresh(new_country)
        return new_country
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(CountryModel).where(CountryModel.code == country_code)
        )
        return result.scalar_one()

async def get_or_create_entities(db: AsyncSession, model, names: list[str]) -> list:
    entities = []
    for name in names:
        result = await db.execute(select(model).where(model.name == name))
        entity = result.scalar_one_or_none()
        if not entity:
            entity = model(name=name)
            db.add(entity)
            await db.flush()
        entities.append(entity)
    return entities


@router.get("/movies/", response_model=MovieListResponse)
async def get_movies(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20)
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(MovieModel)
        .order_by(desc(MovieModel.id))
        .offset(offset)
        .limit(per_page))
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    total_items = await db.scalar(select(func.count()).select_from(MovieModel))
    total_pages = (total_items + per_page - 1) // per_page

    path = request.url.path
    prev_page = f"{path}?page={page - 1}&per_page={per_page}" if page > 1 else None
    next_page = f"{path}?page={page + 1}&per_page={per_page}" if page < total_pages else None

    return MovieListResponse(
        movies=movies,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items
    )


@router.post("/movies/", response_model=MovieCreateResponse)
async def create_movie(
    movie: MovieCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    exists = await db.scalar(
        select(MovieModel).where(
            MovieModel.name == movie.name,
            MovieModel.date == movie.date
        )
    )
    if exists:
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie.name}' and release date '{movie.date}' already exists"
        )

    country = await get_or_create_country(db, movie.country)
    genres = await get_or_create_entities(db, GenreModel, movie.genres)
    actors = await get_or_create_entities(db, ActorModel, movie.actors)
    languages = await get_or_create_entities(db, LanguageModel, movie.languages)

    new_movie = MovieModel(
        **movie.model_dump(exclude={"country", "genres", "actors", "languages"}),
        country_id=country.id,
        genres=genres,
        actors=actors,
        languages=languages,
    )

    db.add(new_movie)
    await db.commit()

    await db.refresh(
        new_movie,
        ["country", "genres", "actors", "languages"]
    )

    return MovieCreateResponse.model_validate(new_movie)


@router.get("/movies/{movie_id}/", response_model=MovieDetailResponse)
async def get_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    return movie


@router.delete("/movies/{movie_id}/")
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    await db.delete(movie)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/movies/{movie_id}/")
async def update_movie(
        movie_id: int,
        movie: MovieUpdateResponse,
        db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    db_movie = result.scalar_one_or_none()

    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    if movie.budget < 0 or movie.revenue < 0:
        raise HTTPException(status_code=400, detail="Invalid input data.")

    if movie.name:
        db_movie.name = movie.name
    if movie.date:
        db_movie.date = movie.date
    if movie.score:
        db_movie.score = movie.score
    if movie.overview:
        db_movie.overview = movie.overview
    if movie.status:
        db_movie.status = movie.status
    if movie.budget:
        db_movie.budget = movie.budget
    if movie.revenue:
        db_movie.revenue = movie.revenue

    await db.commit()
    await db.refresh(db_movie)
    return { "message": "Movie updated successfully." }
