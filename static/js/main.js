var currentMovie = {};
var isHeroSearchPending = false;
var isWatchSubmitPending = false;
var isInfoWatchPending = false;
var searchController = null;
var heroOptionsController = null;

function setButtonLoading(btn, loading, loadingHtml, idleHtml) {
  if (!btn) return;
  btn.disabled = !!loading;
  if (loading) {
    btn.dataset.idleHtml = idleHtml || btn.innerHTML;
    btn.innerHTML = loadingHtml;
  } else {
    btn.innerHTML = btn.dataset.idleHtml || idleHtml || btn.innerHTML;
  }
}

function humanizeName(name) {
  return name.replace(/([a-z])([A-Z])/g, "$1 $2");
}

function isMovieDetailIncomplete(movie) {
  if (!movie) return true;
  if (!movie.cast_list || movie.cast_list.length === 0) return true;
  if (!movie.director || String(movie.director).trim() === "") return true;
  if (Number(movie.runtime || 0) <= 0) return true;
  if (!movie.genres_list || movie.genres_list.length === 0) return true;
  if (!movie.overview || String(movie.overview).trim() === "") return true;
  if (!movie.keywords_list || movie.keywords_list.length === 0) return true;
  var hasNumericGenres = (movie.genres_list || []).some(function (g) {
    return /^\d+$/.test(String(g || "").trim());
  });
  return hasNumericGenres;
}

function fillInfoModal(movie) {
  var poster = document.getElementById("infoPoster");
  var fallback = document.getElementById("infoPosterFallback");
  poster.style.display = "";
  fallback.style.display = "none";
  poster.src = movie.poster_path
    ? "https://image.tmdb.org/t/p/w500" + movie.poster_path
    : "";
  if (!movie.poster_path) {
    poster.style.display = "none";
    fallback.style.display = "flex";
  }
  document.getElementById("infoTitle").innerText = movie.title || "Sin título";
  document.getElementById("infoGenres").innerText =
    (movie.genres_list || []).join(", ") || "No disponible";
  document.getElementById("infoCast").innerText =
    (movie.cast_list || []).map(humanizeName).join(", ") || "No disponible";
  document.getElementById("infoDirector").innerText = humanizeName(
    movie.director || "No disponible",
  );
  document.getElementById("infoRuntime").innerText =
    Number(movie.runtime || 0) > 0 ? Math.round(movie.runtime) + " minutos" : "No disponible";
  document.getElementById("infoRating").innerHTML =
    '<i class="fa-solid fa-star text-warning me-1"></i>' + (movie.vote_average || 0);

  var infoOverview = document.getElementById("infoOverview");
  if (infoOverview) {
    infoOverview.innerText = movie.overview || "Sinopsis no disponible";
  }

  var infoKeywords = document.getElementById("infoKeywords");
  if (infoKeywords) {
    infoKeywords.innerText = (movie.keywords_list || []).slice(0, 8).join(" · ") || "Keywords no disponibles";
  }
}

/* --- Abrir modal de INFO (Top 10, busqueda) --- */
function abrirInfo(movie) {
  currentMovie = movie || {};

  if (!isMovieDetailIncomplete(currentMovie)) {
    fillInfoModal(currentMovie);
    new bootstrap.Modal(document.getElementById("infoModal")).show();
    return;
  }

  if (!currentMovie.id) {
    fillInfoModal(currentMovie);
    new bootstrap.Modal(document.getElementById("infoModal")).show();
    return;
  }

  fetch("/api/movie/" + encodeURIComponent(currentMovie.id))
    .then(function (r) {
      if (!r.ok) throw new Error("No detail");
      return r.json();
    })
    .then(function (detail) {
      currentMovie = Object.assign({}, currentMovie, detail || {});
      fillInfoModal(currentMovie);
      new bootstrap.Modal(document.getElementById("infoModal")).show();
    })
    .catch(function () {
      fillInfoModal(currentMovie);
      new bootstrap.Modal(document.getElementById("infoModal")).show();
    });
}

/* --- Desde Info -> abrir Watch --- */
function abrirWatchDesdeInfo() {
  if (isInfoWatchPending) return;
  isInfoWatchPending = true;
  var infoWatchBtn = document.getElementById("infoWatchBtn");
  if (infoWatchBtn) {
    infoWatchBtn.disabled = true;
  }
  bootstrap.Modal.getInstance(document.getElementById("infoModal")).hide();
  setTimeout(function () {
    abrirWatch(currentMovie);
    isInfoWatchPending = false;
    if (infoWatchBtn) {
      infoWatchBtn.disabled = false;
    }
  }, 350);
}

/* --- Abrir modal de VER (minutos + reaccion) --- */
function abrirWatch(movie) {
  currentMovie = movie;
  var runtime = Math.round(movie.runtime);
  document.getElementById("watchTitle").innerText = movie.title;
  document.getElementById("watchTitulo").value = movie.title;
  var watchMovieId = document.getElementById("watchMovieId");
  if (watchMovieId) {
    watchMovieId.value = movie.id || "";
  }
  document.getElementById("watchRange").max = runtime;
  document.getElementById("watchRange").value = runtime;
  document.getElementById("watchMaxLabel").innerText = runtime + " min";
  document.getElementById("watchRangeValue").innerText = runtime + " min";
  document.getElementById("rLike").checked = true;
  new bootstrap.Modal(document.getElementById("watchModal")).show();
}

/* --- Desde Explicacion -> cerrar y abrir Watch --- */
function cerrarYWatch(movie, modalId) {
  var el = document.getElementById(modalId);
  var instance = bootstrap.Modal.getInstance(el);
  if (instance) instance.hide();
  setTimeout(function () {
    abrirWatch(movie);
  }, 350);
}

/* --- BUSCADOR con autocomplete --- */
var searchTimeout;
var searchInput = document.getElementById("searchInput");
var searchResults = document.getElementById("searchResults");

searchInput.addEventListener("input", function () {
  clearTimeout(searchTimeout);
  var q = this.value.trim();
  if (q.length < 2) {
    searchResults.style.display = "none";
    return;
  }
  searchTimeout = setTimeout(function () {
    if (searchController) {
      searchController.abort();
    }
    searchController = new AbortController();

    fetch("/api/buscar?q=" + encodeURIComponent(q), {
      signal: searchController.signal,
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (q !== searchInput.value.trim()) {
          return;
        }
        if (data.length === 0) {
          searchResults.innerHTML =
            '<div class="p-3 text-secondary text-center small">No se encontraron resultados</div>';
          searchResults.style.display = "block";
          return;
        }
        searchResults.innerHTML = data
          .map(function (m) {
            var posterSrc = m.poster_path
              ? "https://image.tmdb.org/t/p/w92" + m.poster_path
              : "";
            var genres = (m.genres_list || []).join(", ");
            var runtimeLabel =
              Number(m.runtime || 0) > 0
                ? Math.round(m.runtime) + " min"
                : "Duración N/D";
            return (
              '<div class="search-item" onclick=\'abrirInfo(' +
              JSON.stringify(m).replace(/'/g, "\\'") +
              ")'>" +
              (posterSrc
                ? '<img src="' + posterSrc + '" class="search-thumb">'
                : '<div class="search-thumb" style="background:#1a1a2e;border-radius:4px"></div>') +
              "<div>" +
              '<div class="fw-bold small">' +
              m.title +
              "</div>" +
              '<div class="text-secondary" style="font-size:0.7rem">' +
              genres +
              " &middot; " +
              runtimeLabel +
              "</div>" +
              "</div></div>"
            );
          })
          .join("");
        searchResults.style.display = "block";
      })
      .catch(function (err) {
        if (err && err.name === "AbortError") return;
      });
  }, 300);
});

document.addEventListener("click", function (e) {
  if (
    !searchInput.contains(e.target) &&
    !searchResults.contains(e.target)
  ) {
    searchResults.style.display = "none";
  }
});

/* --- HERO POR CHIPS (TMDB + filtros por dimensión) --- */
var heroDimButtons = document.querySelectorAll(".hero-dim-btn");
var heroLogicButtons = document.querySelectorAll(".hero-logic-btn");
var heroFacetInput = document.getElementById("heroFacetInput");
var heroFacetResults = document.getElementById("heroFacetResults");
var heroSelectedChips = document.getElementById("heroSelectedChips");
var heroSummary = document.getElementById("heroSummary");
var btnHeroSearch = document.getElementById("btnHeroSearch");
var heroFallbackMsg = document.getElementById("heroFallbackMsg");
var advancedSection = document.getElementById("advancedSection");
var advancedResultsRow = document.getElementById("advancedResultsRow");

var heroState = {
  activeDimension: "genre",
  logicMode: "and",
  selected: {
    genres: [],
    keywords: [],
    actors: [],
    directors: [],
    collections: [],
  },
};

var dimMap = {
  genre: "genres",
  keyword: "keywords",
  actor: "actors",
  director: "directors",
  collection: "collections",
};

var dimLabel = {
  genre: "género",
  keyword: "keyword",
  actor: "actor",
  director: "director",
  collection: "saga",
};

function setHeroPlaceholder() {
  if (!heroFacetInput) return;
  var label =
    heroState.activeDimension === "genre"
      ? "Géneros"
      : heroState.activeDimension === "keyword"
        ? "Keywords"
        : heroState.activeDimension === "actor"
          ? "Actores"
          : heroState.activeDimension === "director"
            ? "Directores"
            : "Sagas";
  heroFacetInput.placeholder = "Buscar por " + label + "...";
}

function renderHeroSummary() {
  if (!heroSummary) return;
  var allNames = [];
  Object.keys(heroState.selected).forEach(function (k) {
    heroState.selected[k].forEach(function (it) {
      allNames.push(it.name);
    });
  });

  if (allNames.length === 0) {
    heroSummary.innerHTML =
      'Deseas buscar algo con: <span class="text-secondary">(aún sin filtros)</span> <span class="text-secondary">· modo <b>' +
      String(heroState.logicMode || "and").toUpperCase() +
      "</b></span>";
    return;
  }
  heroSummary.innerHTML =
    "Deseas buscar algo con: <span style='color:#c4b5fd'>" +
    allNames.join(", ") +
    "</span> <span class='text-secondary'>· modo <b>" +
    String(heroState.logicMode || "and").toUpperCase() +
    "</b></span>";
}

function renderHeroChips() {
  if (!heroSelectedChips) return;
  var chips = [];
  Object.keys(heroState.selected).forEach(function (k) {
    heroState.selected[k].forEach(function (it) {
      chips.push(
        '<span class="hero-chip"><b>' +
          k.slice(0, -1) +
          '</b> ' +
          it.name +
          ' <button type="button" onclick="removeHeroChip(\'' +
          k +
          '\',' +
          it.id +
          ')"><i class="fa-solid fa-xmark"></i></button></span>',
      );
    });
  });

  heroSelectedChips.innerHTML = chips.join("");
  renderHeroSummary();
}

window.removeHeroChip = function (bucket, id) {
  if (!heroState.selected[bucket]) return;
  heroState.selected[bucket] = heroState.selected[bucket].filter(function (x) {
    return Number(x.id) !== Number(id);
  });
  renderHeroChips();
};

function addHeroOption(option) {
  var bucket = dimMap[heroState.activeDimension];
  if (!bucket) return;

  var exists = heroState.selected[bucket].some(function (x) {
    return Number(x.id) === Number(option.id);
  });
  if (exists) return;

  heroState.selected[bucket].push({ id: option.id, name: option.name });
  heroFacetInput.value = "";
  heroFacetResults.style.display = "none";
  renderHeroChips();
}

function renderHeroOptions(options) {
  if (!heroFacetResults) return;
  if (!options || options.length === 0) {
    heroFacetResults.innerHTML =
      '<div class="p-3 text-secondary text-center small">Sin opciones</div>';
    heroFacetResults.style.display = "block";
    return;
  }

  heroFacetResults.innerHTML = options
    .map(function (o) {
      return (
        '<div class="search-item" onclick="pickHeroOption(' +
        o.id +
        ',\'' +
        String(o.name || "").replace(/'/g, "\\'") +
        '\')">' +
        '<div><div class="fw-bold small">' +
        o.name +
        "</div></div></div>"
      );
    })
    .join("");
  heroFacetResults.style.display = "block";
}

window.pickHeroOption = function (id, name) {
  addHeroOption({ id: id, name: name });
};

function fetchHeroOptions() {
  if (!heroFacetInput || !heroFacetResults) return;
  var q = heroFacetInput.value.trim();
  if (heroState.activeDimension !== "genre" && q.length < 2) {
    heroFacetResults.style.display = "none";
    return;
  }

  fetch(
    "/api/hero/options?dimension=" +
      encodeURIComponent(heroState.activeDimension) +
      "&q=" +
      encodeURIComponent(q),
    {
      signal: (function () {
        if (heroOptionsController) {
          heroOptionsController.abort();
        }
        heroOptionsController = new AbortController();
        return heroOptionsController.signal;
      })(),
    },
  )
    .then(function (r) {
      return r.json();
    })
    .then(function (options) {
      if (q !== heroFacetInput.value.trim()) {
        return;
      }
      renderHeroOptions(options || []);
    })
    .catch(function (err) {
      if (err && err.name === "AbortError") return;
      heroFacetResults.style.display = "none";
    });
}

function renderHeroResults(results) {
  if (!advancedResultsRow || !advancedSection) return;

  if (!results || results.length === 0) {
    advancedResultsRow.innerHTML =
      '<div class="p-3 text-secondary small">No encontramos resultados con esos filtros.</div>';
    advancedSection.style.display = "block";
    return;
  }

  advancedResultsRow.innerHTML = results
    .map(function (peli) {
      var poster = peli.poster_path
        ? "https://image.tmdb.org/t/p/w342" + peli.poster_path
        : "";
      return (
        '<div class="movie-card" onclick=\'abrirInfo(' +
        JSON.stringify(peli).replace(/'/g, "\\'") +
        ')\'>' +
        (poster
          ? '<img src="' +
            poster +
            '" class="movie-poster" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';" />' +
            '<div class="no-poster" style="display:none"><i class="fa-solid fa-film fa-2x"></i></div>'
          : '<div class="no-poster"><i class="fa-solid fa-film fa-2x"></i></div>') +
        '<div class="card-title fw-bold">' +
        peli.title +
        "</div>" +
        '<div class="match-badge">' +
        Math.round((peli.vote_average || 0) * 10) / 10 +
        " ★</div>" +
        "</div>"
      );
    })
    .join("");

  advancedSection.style.display = "block";
}

function runHeroSearch() {
  if (!btnHeroSearch) return;
  if (isHeroSearchPending) return;

  isHeroSearchPending = true;
  setButtonLoading(
    btnHeroSearch,
    true,
    '<i class="fa-solid fa-spinner fa-spin me-1"></i> Buscando...',
    btnHeroSearch.innerHTML,
  );

  fetch("/api/hero/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      selected: heroState.selected,
      logicMode: heroState.logicMode,
    }),
  })
    .then(function (r) {
      return r.json();
    })
    .then(function (payload) {
      if (heroFallbackMsg) {
        heroFallbackMsg.innerHTML = payload.fallback
          ? "No hubo coincidencias exactas; te mostramos opciones cercanas."
          : "Coincidencia exacta por tus filtros seleccionados.";
      }
      renderHeroResults(payload.results || []);
    })
    .catch(function () {
      if (heroFallbackMsg) {
        heroFallbackMsg.innerHTML = "No se pudo completar la búsqueda en este momento.";
      }
      renderHeroResults([]);
    })
    .finally(function () {
      isHeroSearchPending = false;
      setButtonLoading(
        btnHeroSearch,
        false,
        "",
        '<i class="fa-solid fa-sparkles me-1"></i> Buscar',
      );
    });
}

if (heroDimButtons && heroDimButtons.length) {
  heroDimButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      heroDimButtons.forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      heroState.activeDimension = btn.getAttribute("data-dimension") || "genre";
      setHeroPlaceholder();
      heroFacetInput.value = "";
      heroFacetResults.style.display = "none";
    });
  });
}

if (heroLogicButtons && heroLogicButtons.length) {
  heroLogicButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      heroLogicButtons.forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      var value = (btn.getAttribute("data-logic") || "and").toLowerCase();
      heroState.logicMode = ["and", "or", "not"].includes(value) ? value : "and";
      renderHeroSummary();
    });
  });
}

if (heroFacetInput) {
  var heroDebounce;
  heroFacetInput.addEventListener("input", function () {
    clearTimeout(heroDebounce);
    heroDebounce = setTimeout(fetchHeroOptions, 300);
  });
  heroFacetInput.addEventListener("focus", function () {
    fetchHeroOptions();
  });
}

if (btnHeroSearch) {
  btnHeroSearch.addEventListener("click", runHeroSearch);
}

function hydrateRecommendationModal(modalEl) {
  if (!modalEl) return;
  if (modalEl.dataset.hydrated === "1" || modalEl.dataset.loading === "1") return;

  var movieId = Number(modalEl.getAttribute("data-movie-id") || 0);
  if (!movieId) return;

  modalEl.dataset.loading = "1";
  fetch("/api/movie/" + encodeURIComponent(movieId))
    .then(function (r) {
      if (!r.ok) throw new Error("No detail");
      return r.json();
    })
    .then(function (detail) {
      var overviewEl = modalEl.querySelector('[data-role="modal-overview"]');
      var keywordsEl = modalEl.querySelector('[data-role="modal-keywords"]');

      if (overviewEl) {
        overviewEl.innerText = detail.overview || "Sinopsis no disponible";
      }
      if (keywordsEl) {
        keywordsEl.innerText = (detail.keywords_list || []).slice(0, 8).join(" · ") || "Keywords no disponibles";
      }

      modalEl.dataset.hydrated = "1";
    })
    .catch(function () {
      return;
    })
    .finally(function () {
      modalEl.dataset.loading = "0";
    });
}

document
  .querySelectorAll('.modal[id^="explModal"], .modal[id^="explSecModal"]')
  .forEach(function (modalEl) {
    modalEl.addEventListener("show.bs.modal", function () {
      hydrateRecommendationModal(modalEl);
    });
  });

var watchForm = document.getElementById("watchForm");
var watchSubmitBtn = document.getElementById("watchSubmitBtn");
if (watchForm && watchSubmitBtn) {
  watchForm.addEventListener("submit", function (e) {
    if (isWatchSubmitPending) {
      e.preventDefault();
      return;
    }
    isWatchSubmitPending = true;
    setButtonLoading(
      watchSubmitBtn,
      true,
      '<i class="fa-solid fa-spinner fa-spin me-2"></i>PROCESANDO...',
      watchSubmitBtn.innerHTML,
    );
  });

  var watchModal = document.getElementById("watchModal");
  if (watchModal) {
    watchModal.addEventListener("hidden.bs.modal", function () {
      isWatchSubmitPending = false;
      setButtonLoading(
        watchSubmitBtn,
        false,
        "",
        '<i class="fa-solid fa-wand-magic-sparkles me-2"></i>OBTENER RECOMENDACIONES',
      );
    });
  }
}

document.addEventListener("click", function (e) {
  if (!heroFacetInput || !heroFacetResults) return;
  if (!heroFacetInput.contains(e.target) && !heroFacetResults.contains(e.target)) {
    heroFacetResults.style.display = "none";
  }
});

setHeroPlaceholder();
renderHeroChips();
