
from pathlib import Path
from functools import lru_cache
import os
import re

import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


# =========================================================
# 1. CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env", override=True)

DATASET_PATH = BASE_DIR / "dataset" / "movie_ratings.csv"
RECOMMENDATION_PATH = BASE_DIR / "recommendations.csv"
GRAPHX_RECOMMENDATION_PATH = BASE_DIR / "graphx_recommendations.csv"

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").strip()

TMDB_READ_ACCESS_TOKEN = os.getenv(
    "TMDB_READ_ACCESS_TOKEN", ""
).strip()

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


# =========================================================
# 2. FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="CineMatch API",
    description="Movie discovery and hybrid ALS + GraphX recommendations",
    version="6.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://glorious-space-parakeet-q77qp4rgxxgqc96w5-5173.app.github.dev",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# 3. LOAD DATASETS
# =========================================================

def read_csv_or_empty(path):
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        return pd.DataFrame()


movies_df = read_csv_or_empty(DATASET_PATH)

recommendations_df = read_csv_or_empty(
    RECOMMENDATION_PATH
)

graphx_recommendations_df = read_csv_or_empty(
    GRAPHX_RECOMMENDATION_PATH
)


# =========================================================
# 4. HELPER FUNCTIONS
# =========================================================

def find_column(df, *names):
    lookup = {
        str(column).lower(): column
        for column in df.columns
    }

    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]

    return None


def clean_movie_frame():

    if movies_df.empty:
        return pd.DataFrame(
            columns=["movieId", "title", "genres"]
        )

    movie_id_col = find_column(
        movies_df, "movieId", "movie_id", "itemId"
    )

    title_col = find_column(
        movies_df, "title", "movieTitle", "movie_name"
    )

    genres_col = find_column(
        movies_df, "genres", "genre"
    )

    if movie_id_col is None or title_col is None:
        return pd.DataFrame(
            columns=["movieId", "title", "genres"]
        )

    result = pd.DataFrame({
        "movieId": movies_df[movie_id_col],
        "title": movies_df[title_col].fillna("").astype(str),
        "genres": (
            movies_df[genres_col].fillna("").astype(str)
            if genres_col else ""
        )
    })

    result["movieId"] = pd.to_numeric(
        result["movieId"], errors="coerce"
    )

    result = result.dropna(subset=["movieId"])

    result["movieId"] = result["movieId"].astype(int)

    result = result[
        result["title"].str.strip() != ""
    ]

    result = result.drop_duplicates(
        subset=["movieId"]
    )

    return result.reset_index(drop=True)


movie_catalog = clean_movie_frame()


# =========================================================
# 5. RATING STATISTICS
# =========================================================

def build_rating_stats():

    if movies_df.empty:
        return pd.DataFrame(
            columns=["movieId", "average_rating", "rating_count"]
        )

    movie_id_col = find_column(
        movies_df, "movieId", "movie_id", "itemId"
    )

    rating_col = find_column(
        movies_df, "rating", "user_rating", "score"
    )

    if movie_id_col is None or rating_col is None:
        return pd.DataFrame(
            columns=["movieId", "average_rating", "rating_count"]
        )

    ratings = movies_df[
        [movie_id_col, rating_col]
    ].copy()

    ratings.columns = ["movieId", "rating"]

    ratings["movieId"] = pd.to_numeric(
        ratings["movieId"], errors="coerce"
    )

    ratings["rating"] = pd.to_numeric(
        ratings["rating"], errors="coerce"
    )

    ratings = ratings.dropna(
        subset=["movieId", "rating"]
    )

    stats = (
        ratings.groupby("movieId")["rating"]
        .agg(
            average_rating="mean",
            rating_count="count"
        )
        .reset_index()
    )

    stats["movieId"] = stats["movieId"].astype(int)

    stats["average_rating"] = stats[
        "average_rating"
    ].round(2)

    stats["rating_count"] = stats[
        "rating_count"
    ].astype(int)

    return stats


rating_stats = build_rating_stats()


def movie_list(limit=30):

    if movie_catalog.empty:
        return []

    return movie_catalog.head(limit).to_dict(
        orient="records"
    )


def enrich_with_stats(frame):

    if frame.empty:
        return frame

    if rating_stats.empty:
        frame = frame.copy()
        frame["average_rating"] = None
        frame["rating_count"] = 0
        return frame

    return frame.merge(
        rating_stats,
        on="movieId",
        how="left"
    ).fillna({"rating_count": 0})


# =========================================================
# 6. HOME AND HEALTH
# =========================================================

@app.get("/")
def home():

    return {
        "message": "CineMatch API is running",
        "version": "6.0.0",
        "features": [
            "Top-rated movies",
            "Popular movies",
            "Genre filtering",
            "Movie search",
            "Movie details",
            "ALS recommendations",
            "GraphX recommendations",
            "Hybrid recommendations",
            "TMDB movie posters"
        ]
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "dataset_rows": int(len(movies_df)),
        "movies_loaded": int(len(movie_catalog)),
        "recommendations_loaded": int(len(recommendations_df)),
        "graphx_recommendations_loaded": int(
            len(graphx_recommendations_df)
        ),
        "rating_statistics_available": not rating_stats.empty,
        "tmdb_api_key_configured": bool(TMDB_API_KEY),
        "tmdb_read_token_configured": bool(
            TMDB_READ_ACCESS_TOKEN
        ),
        "tmdb_configured": bool(
            TMDB_API_KEY or TMDB_READ_ACCESS_TOKEN
        )
    }


# =========================================================
# 7. TMDB REQUEST
# =========================================================

def tmdb_request(endpoint, params=None):

    request_params = dict(params or {})

    headers = {
        "accept": "application/json"
    }

    if TMDB_READ_ACCESS_TOKEN:

        headers["Authorization"] = (
            f"Bearer {TMDB_READ_ACCESS_TOKEN}"
        )

    elif TMDB_API_KEY:

        request_params["api_key"] = TMDB_API_KEY

    else:

        raise HTTPException(
            status_code=500,
            detail="TMDB credentials are missing from backend/.env"
        )

    try:

        response = requests.get(
            f"{TMDB_BASE_URL}{endpoint}",
            params=request_params,
            headers=headers,
            timeout=20
        )

        if response.status_code == 401:

            raise HTTPException(
                status_code=502,
                detail="TMDB authentication failed. Verify your credentials."
            )

        if response.status_code == 403:

            raise HTTPException(
                status_code=502,
                detail="TMDB access denied. Check your API access."
            )

        response.raise_for_status()

        return response.json()

    except requests.Timeout:

        raise HTTPException(
            status_code=504,
            detail="TMDB request timed out."
        )

    except requests.RequestException as exc:

        raise HTTPException(
            status_code=502,
            detail=f"TMDB request failed: {str(exc)}"
        )


@app.get("/tmdb-test")
def tmdb_test():

    data = tmdb_request(
        "/search/movie",
        {"query": "The Dark Knight"}
    )

    results = data.get("results", [])

    return {
        "status": "success",
        "message": "TMDB authentication is working",
        "results_found": len(results),
        "sample_movie": (
            results[0].get("title") if results else None
        )
    }


# =========================================================
# 8. MOVIE ROUTES
# =========================================================

@app.get("/movies")
def get_movies(
    limit: int = Query(1000, ge=1, le=5000)
):

    return movie_list(limit)


@app.get("/genres")
def get_genres():

    if movie_catalog.empty:
        return []

    genres = set()

    for value in movie_catalog["genres"].fillna(""):

        for genre in str(value).split("|"):

            genre = genre.strip()

            if genre and genre.lower() != "(no genres listed)":
                genres.add(genre)

    return sorted(genres)


@app.get("/top-rated")
def get_top_rated(
    limit: int = Query(100, ge=1, le=500),
    min_votes: int = Query(5, ge=1),
    min_rating: float = Query(0, ge=0, le=5),
    genre: str = Query("All"),
    sort: str = Query(
        "rating",
        pattern="^(rating|popular|title)$"
    )
):

    if movie_catalog.empty:
        return []

    if rating_stats.empty:

        raise HTTPException(
            status_code=503,
            detail="Rating statistics unavailable. Check your dataset."
        )

    result = enrich_with_stats(
        movie_catalog.copy()
    )

    result = result[
        result["rating_count"] >= min_votes
    ]

    result = result[
        result["average_rating"] >= min_rating
    ]

    if genre and genre.lower() != "all":

        result = result[
            result["genres"].fillna("").str.split("|").apply(
                lambda values: genre.lower() in [
                    value.strip().lower()
                    for value in values
                ]
            )
        ]

    if sort == "popular":

        result = result.sort_values(
            ["rating_count", "average_rating"],
            ascending=False
        )

    elif sort == "title":

        result = result.sort_values("title")

    else:

        result = result.sort_values(
            ["average_rating", "rating_count"],
            ascending=False
        )

    return result.head(limit).fillna("").to_dict(
        orient="records"
    )


@app.get("/popular")
def get_popular(
    limit: int = Query(20, ge=1, le=100)
):

    if movie_catalog.empty:
        return []

    if rating_stats.empty:

        raise HTTPException(
            status_code=503,
            detail="Rating statistics unavailable."
        )

    result = enrich_with_stats(
        movie_catalog.copy()
    )

    result = result.sort_values(
        ["rating_count", "average_rating"],
        ascending=False
    ).head(limit)

    return result.fillna("").to_dict(
        orient="records"
    )


@app.get("/movies/genre/{genre_name}")
def get_movies_by_genre(
    genre_name: str,
    limit: int = Query(100, ge=1, le=500),
    sort: str = Query(
        "rating",
        pattern="^(rating|popular|title)$"
    )
):

    if movie_catalog.empty:
        return []

    mask = movie_catalog["genres"].fillna("").str.split("|").apply(
        lambda values: genre_name.casefold() in [
            value.strip().casefold()
            for value in values
        ]
    )

    result = enrich_with_stats(
        movie_catalog[mask].copy()
    )

    if sort == "title":

        result = result.sort_values("title")

    elif sort == "popular":

        result = result.sort_values(
            ["rating_count", "average_rating"],
            ascending=False
        )

    else:

        result = result.sort_values(
            ["average_rating", "rating_count"],
            ascending=False,
            na_position="last"
        )

    return result.head(limit).fillna("").to_dict(
        orient="records"
    )


@app.get("/search")
def search_movies(
    q: str = Query(..., min_length=1),
    limit: int = Query(30, ge=1, le=100)
):

    if movie_catalog.empty:
        return []

    query = q.strip()

    if not query:
        return []

    result = movie_catalog[
        movie_catalog["title"].str.contains(
            re.escape(query),
            case=False,
            na=False,
            regex=True
        )
    ].copy()

    result = enrich_with_stats(result)

    result = result.sort_values(
        ["rating_count", "average_rating"],
        ascending=False
    )

    return result.head(limit).fillna("").to_dict(
        orient="records"
    )


@app.get("/movie/{movie_id}")
def get_movie(movie_id: int):

    if movie_catalog.empty:

        raise HTTPException(
            status_code=503,
            detail="Movie catalogue unavailable"
        )

    match = movie_catalog[
        movie_catalog["movieId"] == movie_id
    ]

    if match.empty:

        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )

    result = enrich_with_stats(
        match.copy()
    ).iloc[0].to_dict()

    return {
        key: None if pd.isna(value) else value
        for key, value in result.items()
    }


# =========================================================
# 9. USERS
# =========================================================

@app.get("/users")
def get_users():

    user_col = find_column(
        movies_df, "userId", "user_id"
    )

    if user_col is None:

        return {
            "total_users": 0,
            "users": []
        }

    ids = sorted(
        pd.to_numeric(
            movies_df[user_col],
            errors="coerce"
        ).dropna().astype(int).unique().tolist()
    )

    return {
        "total_users": len(ids),
        "users": ids
    }


# =========================================================
# 10. ALS RECOMMENDATIONS
# =========================================================

@app.get("/recommend/{user_id}")
def recommend_movies(
    user_id: int,
    limit: int = Query(10, ge=1, le=20)
):

    if recommendations_df.empty:

        raise HTTPException(
            status_code=503,
            detail="Run train_model.py first to generate recommendations.csv"
        )

    user_col = find_column(
        recommendations_df, "userId", "user_id"
    )

    if user_col is None:

        raise HTTPException(
            status_code=500,
            detail="recommendations.csv has no userId column"
        )

    rows = recommendations_df[
        pd.to_numeric(
            recommendations_df[user_col],
            errors="coerce"
        ) == user_id
    ].copy()

    if rows.empty:

        raise HTTPException(
            status_code=404,
            detail=f"No recommendations found for user {user_id}"
        )

    rating_col = find_column(
        rows, "predicted_rating", "prediction", "rating"
    )

    if rating_col:

        rows[rating_col] = pd.to_numeric(
            rows[rating_col], errors="coerce"
        )

        rows = rows.sort_values(
            rating_col,
            ascending=False
        )

    return rows.head(limit).fillna("").to_dict(
        orient="records"
    )


# =========================================================
# 11. HYBRID RECOMMENDATION SYSTEM
# =========================================================

@app.get("/hybrid-recommend/{user_id}")
def hybrid_recommend_movies(
    user_id: int,
    limit: int = Query(10, ge=1, le=20)
):

    if recommendations_df.empty and graphx_recommendations_df.empty:

        raise HTTPException(
            status_code=503,
            detail="No ALS or GraphX recommendations available."
        )

    def prepare_recommendations(
        df,
        score_names,
        output_score
    ):

        if df.empty:

            return pd.DataFrame(
                columns=["movieId", output_score]
            )

        user_col = find_column(
            df, "userId", "user_id"
        )

        movie_col = find_column(
            df, "movieId", "movie_id", "itemId"
        )

        score_col = find_column(
            df, *score_names
        )

        if (
            user_col is None
            or movie_col is None
            or score_col is None
        ):

            return pd.DataFrame(
                columns=["movieId", output_score]
            )

        result = df.copy()

        result[user_col] = pd.to_numeric(
            result[user_col], errors="coerce"
        )

        result[movie_col] = pd.to_numeric(
            result[movie_col], errors="coerce"
        )

        result[score_col] = pd.to_numeric(
            result[score_col], errors="coerce"
        )

        result = result[
            result[user_col] == user_id
        ]

        result = result.dropna(
            subset=[movie_col, score_col]
        )

        result = result.rename(
            columns={
                movie_col: "movieId",
                score_col: output_score
            }
        )

        return result[
            ["movieId", output_score]
        ].copy()

    # Get ALS recommendations
    als = prepare_recommendations(
        recommendations_df,
        [
            "predicted_rating",
            "prediction",
            "rating"
        ],
        "als_score"
    )

    # Get GraphX recommendations
    graphx = prepare_recommendations(
        graphx_recommendations_df,
        [
            "graph_score",
            "predicted_rating",
            "prediction",
            "rating"
        ],
        "graph_score"
    )

    if als.empty and graphx.empty:

        raise HTTPException(
            status_code=404,
            detail=f"No recommendations found for user {user_id}"
        )

    # Merge ALS and GraphX
    combined = pd.merge(
        als,
        graphx,
        on="movieId",
        how="outer"
    )

    combined["als_score"] = pd.to_numeric(
        combined["als_score"],
        errors="coerce"
    )

    combined["graph_score"] = pd.to_numeric(
        combined["graph_score"],
        errors="coerce"
    )

    # 60% ALS + 40% GraphX
    combined["hybrid_score"] = (
        0.60 * combined["als_score"]
        + 0.40 * combined["graph_score"]
    )

    # If only GraphX exists, use GraphX score
    combined.loc[
        combined["als_score"].isna(),
        "hybrid_score"
    ] = combined.loc[
        combined["als_score"].isna(),
        "graph_score"
    ]

    # If only ALS exists, use ALS score
    combined.loc[
        combined["graph_score"].isna(),
        "hybrid_score"
    ] = combined.loc[
        combined["graph_score"].isna(),
        "als_score"
    ]

    # Recommendation source
    combined["recommendation_source"] = "ALS + GraphX"

    combined.loc[
        combined["als_score"].isna(),
        "recommendation_source"
    ] = "GraphX"

    combined.loc[
        combined["graph_score"].isna(),
        "recommendation_source"
    ] = "ALS"

    combined["movieId"] = pd.to_numeric(
        combined["movieId"],
        errors="coerce"
    )

    combined = combined.dropna(
        subset=["movieId", "hybrid_score"]
    )

    combined["movieId"] = combined[
        "movieId"
    ].astype(int)

    # Add movie titles and genres
    if not movie_catalog.empty:

        combined = combined.merge(
            movie_catalog,
            on="movieId",
            how="left"
        )

    if "title" in combined.columns:

        combined = combined.dropna(
            subset=["title"]
        )

    combined = combined.sort_values(
        "hybrid_score",
        ascending=False
    )

    combined = combined.head(limit)

    combined["predicted_rating"] = (
        combined["hybrid_score"]
        .clip(0.5, 5.0)
        .round(2)
    )

    return combined.fillna("").to_dict(
        orient="records"
    )


# =========================================================
# 12. TMDB POSTER FUNCTIONS
# =========================================================

def build_title_variants(title):

    original = str(title).strip()

    year_match = re.search(
        r"\((\d{4})\)\s*$",
        original
    )

    year = (
        year_match.group(1)
        if year_match else None
    )

    without_year = re.sub(
        r"\s*\(\d{4}\)\s*$",
        "",
        original
    ).strip()

    variants = [without_year]

    article_match = re.match(
        r"^(.*),\s*(The|A|An)$",
        without_year,
        re.IGNORECASE
    )

    if article_match:

        variants.append(
            f"{article_match.group(2)} {article_match.group(1)}"
        )

    normalized = re.sub(
        r"[^\w\s]",
        " ",
        without_year
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized
    ).strip()

    if normalized:
        variants.append(normalized)

    return list(
        dict.fromkeys(
            value for value in variants if value
        )
    ), year


@lru_cache(maxsize=2000)
def fetch_movie_poster(title):

    variants, year = build_title_variants(title)

    try:

        for query in variants:

            params = {
                "query": query,
                "include_adult": "false",
                "language": "en-US"
            }

            if year:
                params["year"] = year

            data = tmdb_request(
                "/search/movie",
                params
            )

            results = data.get("results", [])

            poster_results = [
                item for item in results
                if item.get("poster_path")
            ]

            if not poster_results:
                continue

            if year:

                year_matches = [
                    item for item in poster_results
                    if str(
                        item.get("release_date", "")
                    ).startswith(year)
                ]

                if year_matches:
                    poster_results = year_matches

            movie = poster_results[0]

            poster_path = movie.get("poster_path")

            return {
                "title": movie.get("title", title),
                "poster_url": (
                    f"{TMDB_IMAGE_BASE}{poster_path}"
                    if poster_path else None
                ),
                "overview": movie.get("overview", ""),
                "release_date": movie.get("release_date", ""),
                "error": None
            }

        return {
            "title": title,
            "poster_url": None,
            "overview": "",
            "release_date": "",
            "error": "No matching movie poster found on TMDB"
        }

    except HTTPException as exc:

        return {
            "title": title,
            "poster_url": None,
            "overview": "",
            "release_date": "",
            "error": str(exc.detail)
        }

    except Exception as exc:

        return {
            "title": title,
            "poster_url": None,
            "overview": "",
            "release_date": "",
            "error": str(exc)
        }


@app.get("/movie-poster/{title:path}")
def get_movie_poster(title: str):

    if not title.strip():

        raise HTTPException(
            status_code=400,
            detail="Movie title is required"
        )

    return fetch_movie_poster(
        title.strip()
    )
