using Dapper;
using Cinepolis.Api.Models;

namespace Cinepolis.Api.Services;

public interface ICarteleraService
{
    Task<CarteleraResponse> ObtenerCarteleraAsync(string complejoSlug, string? fecha);
    Task<PeliculaDto?> ObtenerPeliculaAsync(int peliculaId);
    Task<MapaSalaResponse?> ObtenerMapaSalaAsync(int funcionId);
}

public class CarteleraService : ICarteleraService
{
    private readonly IDbConnectionFactory _dbFactory;

    public CarteleraService(IDbConnectionFactory dbFactory)
    {
        _dbFactory = dbFactory;
    }

    public async Task<CarteleraResponse> ObtenerCarteleraAsync(string complejoSlug, string? fecha)
    {
        var fechaConsulta = string.IsNullOrWhiteSpace(fecha) 
            ? DateTime.UtcNow.ToString("yyyy-MM-dd") 
            : fecha;

        const string sql = """
            SELECT 
                p.pelicula_id AS PeliculaId, p.titulo AS Titulo, p.clasificacion AS Clasificacion, 
                p.duracion_min AS DuracionMin, p.poster_url AS PosterUrl, p.categoria AS Categoria,
                f.funcion_id AS FuncionId, f.hora_inicio::text AS HoraInicio, 
                fs.nombre_formato AS Formato, f.idioma AS Idioma, 
                s.nombre_sala AS Sala, s.tipo_sala AS TipoSala
            FROM FUNCION f
            JOIN PELICULA p ON f.pelicula_id = p.pelicula_id
            JOIN SALA s ON f.sala_id = s.sala_id
            JOIN COMPLEJO c ON s.complejo_id = c.complejo_id
            JOIN FORMATO_SALA fs ON f.formato_id = fs.formato_id
            WHERE c.slug = @ComplejoSlug AND f.fecha_funcion = @Fecha::date AND f.activa = TRUE
            ORDER BY p.titulo, f.hora_inicio
        """;

        using var db = _dbFactory.CreateConnection();
        var rows = await db.QueryAsync<dynamic>(sql, new { ComplejoSlug = complejoSlug, Fecha = fechaConsulta });

        var peliculasDict = new Dictionary<int, CarteleraPeliculaDto>();

        foreach (var r in rows)
        {
            int pId = (int)r.peliculaid;
            if (!peliculasDict.TryGetValue(pId, out var pDto))
            {
                pDto = new CarteleraPeliculaDto
                {
                    PeliculaId = pId,
                    Titulo = (string)r.titulo,
                    Clasificacion = (string?)r.clasificacion,
                    DuracionMin = (int?)r.duracionmin,
                    PosterUrl = (string?)r.posterurl,
                    Categoria = (string?)r.categoria,
                    Funciones = new List<FuncionDto>()
                };
                peliculasDict[pId] = pDto;
            }

            pDto.Funciones.Add(new FuncionDto
            {
                FuncionId = (int)r.funcionid,
                HoraInicio = (string)r.horainicio,
                Formato = (string)r.formato,
                Idioma = (string)r.idioma,
                Sala = (string)r.sala,
                TipoSala = (string)r.tiposala
            });
        }

        return new CarteleraResponse
        {
            Complejo = complejoSlug,
            FechaConsulta = fechaConsulta,
            TotalPeliculas = peliculasDict.Count,
            Peliculas = peliculasDict.Values.ToList()
        };
    }

    public async Task<PeliculaDto?> ObtenerPeliculaAsync(int peliculaId)
    {
        const string sqlPelicula = """
            SELECT pelicula_id AS PeliculaId, titulo AS Titulo, slug AS Slug, 
                   clasificacion AS Clasificacion, genero AS Genero, duracion_min AS DuracionMin, 
                   sinopsis AS Sinopsis, categoria AS Categoria, poster_url AS PosterUrl, 
                   banner_url AS BannerUrl, trailer_url AS TrailerUrl
            FROM PELICULA
            WHERE pelicula_id = @PeliculaId
        """;

        const string sqlElenco = """
            SELECT per.nombre, pp.rol
            FROM PELICULA_PERSONA pp
            JOIN PERSONA per ON per.persona_id = pp.persona_id
            WHERE pp.pelicula_id = @PeliculaId
            ORDER BY pp.rol DESC, per.nombre
        """;

        using var db = _dbFactory.CreateConnection();
        var pelicula = await db.QueryFirstOrDefaultAsync<PeliculaDto>(sqlPelicula, new { PeliculaId = peliculaId });
        if (pelicula == null) return null;

        var elenco = await db.QueryAsync<dynamic>(sqlElenco, new { PeliculaId = peliculaId });
        foreach (var e in elenco)
        {
            string rol = (string)e.rol;
            string nombre = (string)e.nombre;
            if (rol.ToLower() == "director" && string.IsNullOrEmpty(pelicula.Director))
            {
                pelicula.Director = nombre;
            }
            else if (rol.ToLower() == "actor")
            {
                pelicula.Actores.Add(nombre);
            }
        }

        return pelicula;
    }

    public async Task<MapaSalaResponse?> ObtenerMapaSalaAsync(int funcionId)
    {
        const string sqlFuncion = """
            SELECT p.pelicula_id AS PeliculaId, p.titulo AS Titulo, p.clasificacion AS Clasificacion, 
                   p.duracion_min AS DuracionMin, p.poster_url AS PosterUrl,
                   s.nombre_sala AS Sala, f.hora_inicio::text AS HoraInicio, f.fecha_funcion::text AS FechaFuncion
            FROM FUNCION f 
            JOIN PELICULA p ON f.pelicula_id = p.pelicula_id 
            JOIN SALA s ON f.sala_id = s.sala_id
            WHERE f.funcion_id = @FuncionId
        """;

        const string sqlAsientos = """
            SELECT a.asiento_id AS AsientoId, a.fila AS Fila, a.columna AS Columna, 
                   a.tipo_asiento AS Tipo, a.estado AS Estado, ap.area_category_code AS AreaCode
            FROM ASIENTO a
            JOIN FUNCION f ON a.funcion_id = f.funcion_id
            LEFT JOIN ASIENTO_PLANTILLA ap ON ap.sala_id = f.sala_id AND ap.fila = a.fila AND ap.columna = a.columna
            WHERE a.funcion_id = @FuncionId 
            ORDER BY a.fila, a.columna
        """;

        using var db = _dbFactory.CreateConnection();
        var funcInfo = await db.QueryFirstOrDefaultAsync<dynamic>(sqlFuncion, new { FuncionId = funcionId });
        if (funcInfo == null) return null;

        var asientosRaw = await db.QueryAsync<dynamic>(sqlAsientos, new { FuncionId = funcionId });

        var filas = new Dictionary<string, List<AsientoItemDto>>();
        int totalDisponibles = 0;

        foreach (var a in asientosRaw)
        {
            string fila = (string)a.fila;
            int columna = (int)a.columna;
            string estado = (string)a.estado;

            if (!filas.ContainsKey(fila))
            {
                filas[fila] = new List<AsientoItemDto>();
            }

            filas[fila].Add(new AsientoItemDto
            {
                AsientoId = (int)a.asientoid,
                Columna = columna,
                Etiqueta = $"{fila}{columna}",
                Tipo = (string)a.tipo,
                Estado = estado,
                AreaCode = (string?)a.areacode
            });

            if (estado == "disponible")
            {
                totalDisponibles++;
            }
        }

        return new MapaSalaResponse
        {
            FuncionId = funcionId,
            PeliculaId = (int)funcInfo.peliculaid,
            Pelicula = (string)funcInfo.titulo,
            Clasificacion = (string?)funcInfo.clasificacion,
            DuracionMin = (int?)funcInfo.duracionmin,
            PosterUrl = (string?)funcInfo.posterurl,
            Sala = (string)funcInfo.sala,
            HoraInicio = (string)funcInfo.horainicio,
            FechaFuncion = (string)funcInfo.fechafuncion,
            TotalDisponibles = totalDisponibles,
            Filas = filas
        };
    }
}

