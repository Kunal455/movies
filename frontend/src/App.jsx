
import { useEffect, useState } from "react";
import {
  Search,
  Film,
  Home,
  TrendingUp,
  Star,
  Sparkles,
  Clapperboard,
  X,
  Play,
  LoaderCircle,
  ChevronRight,
  SlidersHorizontal,
  RotateCcw,
} from "lucide-react";
import "./App.css";

const API =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function apiGet(path) {
  const response = await fetch(`${API}${path}`);

  if (!response.ok) {
    let message = "Something went wrong";

    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Ignore invalid error responses.
    }

    throw new Error(message);
  }

  return response.json();
}

// ------------------------------------
// CINEMATIC FALLBACK POSTER
// ------------------------------------

function PosterArtwork({ movie, large = false }) {
  const title = movie?.title || "Untitled Movie";

  const genres = String(
    movie?.genres || movie?.genre || "CINEMATCH ORIGINAL"
  )
    .split("|")[0]
    .split(",")[0]
    .trim();

  const rating =
    movie?.average_rating ??
    movie?.predicted_rating ??
    movie?.rating;

  return (
    <div
      className={`poster-artwork ${
        large ? "poster-artwork-large" : ""
      }`}
    >
      <div className="poster-artwork-glow" />

      <div className="poster-artwork-top">
        <span className="poster-artwork-brand">
          CINEMATCH
        </span>
        <Clapperboard size={20} />
      </div>

      <div className="poster-artwork-center">
        <div className="poster-artwork-orbit poster-artwork-orbit-one" />
        <div className="poster-artwork-orbit poster-artwork-orbit-two" />

        <div className="poster-artwork-icon">
          <Film
            size={large ? 66 : 48}
            strokeWidth={1.25}
          />
        </div>
      </div>

      <div className="poster-artwork-bottom">
        <span className="poster-artwork-genre">
          {genres || "MOVIE"}
        </span>

        <h2>{title}</h2>

        {rating !== undefined &&
          rating !== null &&
          rating !== "" && (
            <span className="poster-artwork-rating">
              <Star size={13} fill="currentColor" />
              {Number(rating).toFixed(1)}
            </span>
          )}
      </div>
    </div>
  );
}

// ------------------------------------
// MOVIE CARD
// ------------------------------------

function MovieCard({ movie, onClick }) {
  const [poster, setPoster] = useState(null);

  useEffect(() => {
    let active = true;

    setPoster(null);

    apiGet(
      `/movie-poster/${encodeURIComponent(movie.title)}`
    )
      .then((data) => {
        if (active && data.poster_url) {
          setPoster(data.poster_url);
        }
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, [movie.title]);

  const rating =
    movie.average_rating ??
    movie.predicted_rating ??
    movie.rating;

  return (
    <button className="movie-card" onClick={onClick}>
      <div className="poster-wrapper">
        {poster ? (
          <img
            src={poster}
            alt={movie.title}
            loading="lazy"
            onError={() => setPoster(null)}
          />
        ) : (
          <PosterArtwork movie={movie} />
        )}

        <div className="poster-overlay">
          <span className="play-circle">
            <Play size={22} fill="currentColor" />
          </span>
        </div>

        {rating !== undefined &&
          rating !== null &&
          rating !== "" && (
            <span className="rating-badge">
              <Star size={13} fill="currentColor" />
              {Number(rating).toFixed(1)}
            </span>
          )}
      </div>

      <div className="movie-info">
        <h3>{movie.title}</h3>
        <p>{movie.genres || "Movie"}</p>

        <div className="rating-details">
          <span>
            <Star size={12} fill="currentColor" />
            {movie.average_rating != null
              ? Number(movie.average_rating).toFixed(1)
              : rating != null
                ? Number(rating).toFixed(1)
                : "N/A"}
          </span>

          <span>
            {movie.rating_count != null
              ? `${movie.rating_count} ratings`
              : movie.predicted_rating != null
                ? "ALS prediction"
                : "No rating data"}
          </span>
        </div>
      </div>
    </button>
  );
}

// ------------------------------------
// MOVIE SECTION
// ------------------------------------

function MovieSection({
  title,
  subtitle,
  movies,
  onMovieClick,
}) {
  if (!movies.length) return null;

  return (
    <section className="movie-section">
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>

        <span className="movie-count">
          {movies.length} movies
        </span>
      </div>

      <div className="movie-grid">
        {movies.map((movie, index) => (
          <MovieCard
            key={`${movie.movieId}-${index}`}
            movie={movie}
            onClick={() => onMovieClick(movie)}
          />
        ))}
      </div>
    </section>
  );
}

// ------------------------------------
// MAIN APP
// ------------------------------------

function App() {
  const [activeTab, setActiveTab] = useState("home");

  const [topMovies, setTopMovies] = useState([]);
  const [popularMovies, setPopularMovies] = useState([]);
  const [allMovies, setAllMovies] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [genres, setGenres] = useState([]);

  const [selectedGenre, setSelectedGenre] = useState("");
  const [selectedMovie, setSelectedMovie] = useState(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [userId, setUserId] = useState("1");

  // Top rated filters
  const [filterGenre, setFilterGenre] = useState("All");
  const [minRating, setMinRating] = useState("0");
  const [minVotes, setMinVotes] = useState("5");
  const [sortBy, setSortBy] = useState("rating");

  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // ------------------------------------
  // LOAD HOME DATA
  // ------------------------------------

  useEffect(() => {
    async function loadHome() {
      setLoading(true);
      setError("");

      try {
        const [
          top,
          popular,
          movies,
          genreList,
        ] = await Promise.all([
          apiGet("/top-rated?limit=12&min_votes=5"),
          apiGet("/popular?limit=12"),
          apiGet("/movies?limit=500"),
          apiGet("/genres"),
        ]);

        setTopMovies(top);
        setPopularMovies(popular);
        setAllMovies(movies);
        setGenres(genreList);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadHome();
  }, []);

  // ------------------------------------
  // TOP RATED FILTERS
  // ------------------------------------

  async function applyTopFilters(
    event,
    customFilters = null
  ) {
    event?.preventDefault();

    const filters = customFilters || {
      genre: filterGenre,
      min_rating: minRating,
      min_votes: minVotes,
      sort: sortBy,
    };

    setActiveTab("top");
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const params = new URLSearchParams({
        limit: "100",
        genre: filters.genre,
        min_rating: filters.min_rating,
        min_votes: filters.min_votes,
        sort: filters.sort,
      });

      const data = await apiGet(
        `/top-rated?${params.toString()}`
      );

      setTopMovies(data);

      if (!data.length) {
        setMessage(
          "No movies match these filters. Try changing your criteria."
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function resetTopFilters() {
    const defaults = {
      genre: "All",
      min_rating: "0",
      min_votes: "5",
      sort: "rating",
    };

    setFilterGenre(defaults.genre);
    setMinRating(defaults.min_rating);
    setMinVotes(defaults.min_votes);
    setSortBy(defaults.sort);

    applyTopFilters(null, defaults);
  }

  // ------------------------------------
  // SEARCH
  // ------------------------------------

  async function handleSearch(event) {
    event?.preventDefault();

    if (!searchQuery.trim()) return;

    setActiveTab("search");
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const data = await apiGet(
        `/search?q=${encodeURIComponent(searchQuery)}&limit=30`
      );

      setSearchResults(data);

      if (!data.length) {
        setMessage("No movies found. Try another title.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ------------------------------------
  // GENRE FILTER
  // ------------------------------------

  async function handleGenre(genre) {
    setSelectedGenre(genre);
    setActiveTab("genre");
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const data = await apiGet(
        `/movies/genre/${encodeURIComponent(genre)}?limit=50&sort=rating`
      );

      setSearchResults(data);

      if (!data.length) {
        setMessage("No movies found in this genre.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ------------------------------------
  // ALS RECOMMENDATIONS
  // ------------------------------------

  async function handleRecommendations(event) {
    event.preventDefault();

    const id = Number(userId);

    if (!Number.isInteger(id) || id < 1) {
      setError("Enter a valid user ID.");
      return;
    }

    setActiveTab("for-you");
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const data = await apiGet(
        `/recommend/${id}?limit=10`
      );

      const mapped = data.map((item) => {
        const movieId =
          item.movieId ??
          item.movie_id ??
          item.itemId;

        const movie = allMovies.find(
          (m) => Number(m.movieId) === Number(movieId)
        );

        return {
          ...movie,
          ...item,
          movieId,
          title:
            item.title ||
            movie?.title ||
            `Movie ${movieId}`,
          genres:
            item.genres ||
            movie?.genres ||
            "Recommended",
          predicted_rating:
            item.predicted_rating ??
            item.prediction ??
            item.rating,
        };
      });

      setRecommendations(mapped);

      if (!mapped.length) {
        setMessage(
          "No recommendations available for this user."
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ------------------------------------
  // NAVIGATION
  // ------------------------------------

  function goHome() {
    setActiveTab("home");
    setSelectedGenre("");
    setSearchQuery("");
    setMessage("");
    setError("");
  }

  function openTopRated() {
    applyTopFilters();
  }

  function openPopular() {
    setActiveTab("popular");
    setError("");
    setMessage("");
  }

  function openForYou() {
    setActiveTab("for-you");
    setError("");
    setMessage("");
  }

  // ------------------------------------
  // MOVIE GRID
  // ------------------------------------

  function renderMovieGrid(movies) {
    if (loading) {
      return (
        <div className="loading-state">
          <LoaderCircle
            className="spinner"
            size={35}
          />
          <p>Finding great movies for you...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="empty-state">
          <Film size={40} />
          <h3>Unable to load movies</h3>
          <p>{error}</p>

          <button
            className="primary-button"
            onClick={goHome}
          >
            Back to home
          </button>
        </div>
      );
    }

    if (!movies.length) {
      return (
        <div className="empty-state">
          <Film size={40} />
          <h3>No movies found</h3>
          <p>
            {message || "Try exploring another section."}
          </p>
        </div>
      );
    }

    return (
      <div className="movie-grid">
        {movies.map((movie, index) => (
          <MovieCard
            key={`${movie.movieId}-${index}`}
            movie={movie}
            onClick={() => setSelectedMovie(movie)}
          />
        ))}
      </div>
    );
  }

  const featuredMovie = topMovies[0];

  // ------------------------------------
  // RENDER
  // ------------------------------------

  return (
    <div className="app">

      {/* NAVBAR */}

      <header className="navbar">
        <button
          className="brand"
          onClick={goHome}
        >
          <span className="brand-icon">
            <Clapperboard size={23} />
          </span>

          <span>
            Cine<span>Match</span>
          </span>
        </button>

        <nav className="nav-links">
          <button
            className={
              activeTab === "home" ? "active" : ""
            }
            onClick={goHome}
          >
            <Home size={17} />
            Home
          </button>

          <button
            className={
              activeTab === "top" ? "active" : ""
            }
            onClick={openTopRated}
          >
            <Star size={17} />
            Top Rated
          </button>

          <button
            className={
              activeTab === "popular" ? "active" : ""
            }
            onClick={openPopular}
          >
            <TrendingUp size={17} />
            Popular
          </button>

          <button
            className={
              activeTab === "for-you" ? "active" : ""
            }
            onClick={openForYou}
          >
            <Sparkles size={17} />
            For You
          </button>
        </nav>

        <form
          className="search-box"
          onSubmit={handleSearch}
        >
          <Search size={18} />

          <input
            value={searchQuery}
            onChange={(event) =>
              setSearchQuery(event.target.value)
            }
            placeholder="Search movies..."
          />

          <button
            type="submit"
            aria-label="Search"
          >
            <ChevronRight size={18} />
          </button>
        </form>
      </header>

      <main>

        {/* HOME PAGE */}

        {activeTab === "home" && (
          <>
            <section className="hero">
              <div className="hero-content">
                <span className="eyebrow">
                  <Sparkles size={15} />
                  YOUR PERSONAL MOVIE WORLD
                </span>

                <h1>
                  Discover movies.
                  <br />
                  Find your <span>next favourite.</span>
                </h1>

                <p>
                  Explore movies, discover hidden gems,
                  and get recommendations powered by
                  machine learning.
                </p>

                <div className="hero-actions">
                  <button
                    className="primary-button"
                    onClick={openPopular}
                  >
                    <Play
                      size={17}
                      fill="currentColor"
                    />
                    Explore Movies
                  </button>

                  <button
                    className="secondary-button"
                    onClick={openForYou}
                  >
                    <Sparkles size={17} />
                    For You
                  </button>
                </div>
              </div>

              {featuredMovie && (
                <div className="hero-feature">
                  <MovieCard
                    movie={featuredMovie}
                    onClick={() =>
                      setSelectedMovie(featuredMovie)
                    }
                  />

                  <span>FEATURED MOVIE</span>
                </div>
              )}
            </section>

            {/* GENRES */}

            <section className="genre-section">
              <div className="section-heading">
                <div>
                  <h2>Explore by Genre</h2>
                  <p>
                    Choose your mood and find a movie.
                  </p>
                </div>
              </div>

              <div className="genre-list">
                {genres.map((genre) => (
                  <button
                    key={genre}
                    onClick={() => handleGenre(genre)}
                    className="genre-chip"
                  >
                    {genre}
                  </button>
                ))}
              </div>
            </section>

            {/* HOME MOVIES */}

            {loading ? (
              <div className="loading-state">
                <LoaderCircle
                  className="spinner"
                  size={35}
                />
                <p>Loading your movie collection...</p>
              </div>
            ) : error ? (
              <div className="empty-state">
                <Film size={40} />
                <h3>Could not load movies</h3>
                <p>{error}</p>
              </div>
            ) : (
              <>
                <MovieSection
                  title="Top Rated Movies"
                  subtitle="Movies loved by viewers"
                  movies={topMovies}
                  onMovieClick={setSelectedMovie}
                />

                <MovieSection
                  title="Popular Movies"
                  subtitle="Movies with the most ratings"
                  movies={popularMovies}
                  onMovieClick={setSelectedMovie}
                />
              </>
            )}
          </>
        )}

        {/* TOP RATED PAGE */}

        {activeTab === "top" && (
          <section className="page-section">

            <div className="page-title">
              <span className="eyebrow">
                <Star size={14} />
                RATING BASED DISCOVERY
              </span>

              <h1>Top Rated Movies</h1>

              <p>
                Discover the best movies based on
                actual viewer ratings.
              </p>
            </div>

            {/* FILTER PANEL */}

            <div className="filter-panel">
              <div className="filter-heading">
                <div>
                  <h2>
                    <SlidersHorizontal size={19} />
                    Filter Movies
                  </h2>

                  <span>
                    Customize your movie discovery.
                  </span>
                </div>
              </div>

              <div className="filter-grid">

                {/* GENRE */}

                <div className="filter-group">
                  <label>Movie Type</label>

                  <select
                    value={filterGenre}
                    onChange={(event) =>
                      setFilterGenre(event.target.value)
                    }
                  >
                    <option value="All">
                      All Genres
                    </option>

                    {genres.map((genre) => (
                      <option
                        key={genre}
                        value={genre}
                      >
                        {genre}
                      </option>
                    ))}
                  </select>
                </div>

                {/* RATING */}

                <div className="filter-group">
                  <label>Minimum Rating</label>

                  <select
                    value={minRating}
                    onChange={(event) =>
                      setMinRating(event.target.value)
                    }
                  >
                    <option value="0">
                      All Ratings
                    </option>
                    <option value="1">1.0+</option>
                    <option value="2">2.0+</option>
                    <option value="3">3.0+</option>
                    <option value="4">4.0+</option>
                    <option value="5">5.0+</option>
                  </select>
                </div>

                {/* VOTES */}

                <div className="filter-group">
                  <label>Minimum Votes</label>

                  <select
                    value={minVotes}
                    onChange={(event) =>
                      setMinVotes(event.target.value)
                    }
                  >
                    <option value="1">1+ Votes</option>
                    <option value="5">5+ Votes</option>
                    <option value="10">10+ Votes</option>
                    <option value="50">50+ Votes</option>
                    <option value="100">100+ Votes</option>
                  </select>
                </div>

                {/* SORT */}

                <div className="filter-group">
                  <label>Sort By</label>

                  <select
                    value={sortBy}
                    onChange={(event) =>
                      setSortBy(event.target.value)
                    }
                  >
                    <option value="rating">
                      Highest Rating
                    </option>
                    <option value="popular">
                      Most Rated
                    </option>
                    <option value="title">
                      Movie Name
                    </option>
                  </select>
                </div>
              </div>

              <div className="filter-actions">
                <button
                  className="primary-button"
                  onClick={applyTopFilters}
                >
                  <SlidersHorizontal size={16} />
                  Apply Filters
                </button>

                <button
                  className="secondary-button"
                  onClick={resetTopFilters}
                >
                  <RotateCcw size={16} />
                  Reset
                </button>
              </div>
            </div>

            {/* RESULTS */}

            <div className="section-heading results-heading">
              <div>
                <h2>Movie Results</h2>
                <p>
                  {loading
                    ? "Loading..."
                    : `${topMovies.length} movies found`}
                </p>
              </div>
            </div>

            {renderMovieGrid(topMovies)}
          </section>
        )}

        {/* POPULAR PAGE */}

        {activeTab === "popular" && (
          <section className="page-section">
            <div className="page-title">
              <span className="eyebrow">
                TRENDING COLLECTION
              </span>

              <h1>Popular Movies</h1>

              <p>
                Discover movies with the most viewer ratings.
              </p>
            </div>

            {renderMovieGrid(popularMovies)}
          </section>
        )}

        {/* SEARCH PAGE */}

        {activeTab === "search" && (
          <section className="page-section">
            <div className="page-title">
              <span className="eyebrow">
                SEARCH RESULTS
              </span>

              <h1>Find your movie</h1>

              <p>
                Results for "{searchQuery}"
              </p>
            </div>

            {renderMovieGrid(searchResults)}
          </section>
        )}

        {/* GENRE PAGE */}

        {activeTab === "genre" && (
          <section className="page-section">
            <div className="page-title">
              <span className="eyebrow">
                EXPLORE GENRES
              </span>

              <h1>{selectedGenre} Movies</h1>

              <p>
                Movies from your selected genre.
              </p>
            </div>

            {renderMovieGrid(searchResults)}
          </section>
        )}

        {/* FOR YOU PAGE */}

        {activeTab === "for-you" && (
          <section className="page-section">
            <div className="page-title">
              <span className="eyebrow">
                <Sparkles size={14} />
                MACHINE LEARNING
              </span>

              <h1>Made For You</h1>

              <p>
                Get personalized recommendations
                from your ALS model.
              </p>
            </div>

            <form
              className="recommend-form"
              onSubmit={handleRecommendations}
            >
              <label htmlFor="userId">
                Enter your MovieLens User ID
              </label>

              <div>
                <input
                  id="userId"
                  type="number"
                  min="1"
                  value={userId}
                  onChange={(event) =>
                    setUserId(event.target.value)
                  }
                  placeholder="Enter user ID"
                />

                <button
                  type="submit"
                  className="primary-button"
                >
                  <Sparkles size={17} />
                  Get Recommendations
                </button>
              </div>
            </form>

            {recommendations.length > 0 && (
              <div className="recommendation-heading">
                <h2>Your Recommendations</h2>
                <span>Powered by ALS</span>
              </div>
            )}

            {renderMovieGrid(recommendations)}
          </section>
        )}
      </main>

      {/* FOOTER */}

      <footer className="footer">
        <div className="brand footer-brand">
          <Clapperboard size={21} />

          <span>
            Cine<span>Match</span>
          </span>
        </div>

        <p>
          Discover more. Watch better.
          Powered by Machine Learning.
        </p>

        <span>© 2026 CineMatch</span>
      </footer>

      {/* MOVIE DETAILS MODAL */}

      {selectedMovie && (
        <MovieModal
          movie={selectedMovie}
          onClose={() => setSelectedMovie(null)}
        />
      )}
    </div>
  );
}

// ------------------------------------
// MOVIE MODAL
// ------------------------------------

function MovieModal({ movie, onClose }) {
  const [poster, setPoster] = useState(null);
  const [details, setDetails] = useState(null);

  useEffect(() => {
    let active = true;

    setPoster(null);
    setDetails(null);

    apiGet(
      `/movie-poster/${encodeURIComponent(movie.title)}`
    )
      .then((data) => {
        if (active) {
          setDetails(data);

          if (data.poster_url) {
            setPoster(data.poster_url);
          }
        }
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, [movie.title]);

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  const rating =
    movie.average_rating ??
    movie.predicted_rating ??
    movie.rating;

  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
    >
      <div
        className="movie-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          className="modal-close"
          onClick={onClose}
        >
          <X size={22} />
        </button>

        {poster ? (
          <img
            className="modal-poster"
            src={poster}
            alt={movie.title}
            onError={() => setPoster(null)}
          />
        ) : (
          <div className="modal-poster modal-poster-fallback">
            <PosterArtwork movie={movie} large />
          </div>
        )}

        <div className="modal-content">
          <span className="eyebrow">
            CINEMATCH DISCOVERY
          </span>

          <h2>{movie.title}</h2>

          <p className="modal-genres">
            {movie.genres || "Movie"}
          </p>

          {rating !== undefined &&
            rating !== null &&
            rating !== "" && (
              <div className="modal-rating">
                <Star size={17} fill="currentColor" />
                {Number(rating).toFixed(2)}
              </div>
            )}

          {movie.rating_count != null && (
            <p className="modal-overview">
              Based on {movie.rating_count} viewer ratings.
            </p>
          )}

          <p className="modal-overview">
            {details?.overview ||
              "Explore this movie from your CineMatch collection."}
          </p>

          {details?.release_date && (
            <p className="release-date">
              Release date: {details.release_date}
            </p>
          )}

          <p className="movie-id">
            Movie ID: {movie.movieId}
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;
