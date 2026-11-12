namespace Cinepolis.Api.Models;

public class PeliculaDto
{
    public int PeliculaId { get; set; }
    public string Titulo { get; set; } = string.Empty;
    public string? Slug { get; set; }
    public string? Clasificacion { get; set; }
    public string? Genero { get; set; }
    public int? DuracionMin { get; set; }
    public string? Sinopsis { get; set; }
    public string? Categoria { get; set; }
    public string? PosterUrl { get; set; }
    public string? BannerUrl { get; set; }
    public string? TrailerUrl { get; set; }
    public string? Director { get; set; }
    public List<string> Actores { get; set; } = new();
}

public class FuncionDto
{
    public int FuncionId { get; set; }
    public string HoraInicio { get; set; } = string.Empty;
    public string Formato { get; set; } = string.Empty;
    public string Idioma { get; set; } = string.Empty;
    public string Sala { get; set; } = string.Empty;
    public string TipoSala { get; set; } = string.Empty;
}

public class CarteleraPeliculaDto
{
    public int PeliculaId { get; set; }
    public string Titulo { get; set; } = string.Empty;
    public string? Clasificacion { get; set; }
    public int? DuracionMin { get; set; }
    public string? PosterUrl { get; set; }
    public string? Categoria { get; set; }
    public List<FuncionDto> Funciones { get; set; } = new();
}

public class CarteleraResponse
{
    public string Complejo { get; set; } = string.Empty;
    public string FechaConsulta { get; set; } = string.Empty;
    public int TotalPeliculas { get; set; }
    public List<CarteleraPeliculaDto> Peliculas { get; set; } = new();
}

public class AsientoItemDto
{
    public int AsientoId { get; set; }
    public int Columna { get; set; }
    public string Etiqueta { get; set; } = string.Empty;
    public string Tipo { get; set; } = string.Empty;
    public string Estado { get; set; } = "disponible";
    public string? AreaCode { get; set; }
}

public class MapaSalaResponse
{
    public int FuncionId { get; set; }
    public int PeliculaId { get; set; }
    public string Pelicula { get; set; } = string.Empty;
    public string? Clasificacion { get; set; }
    public int? DuracionMin { get; set; }
    public string? PosterUrl { get; set; }
    public string Sala { get; set; } = string.Empty;
    public string HoraInicio { get; set; } = string.Empty;
    public string FechaFuncion { get; set; } = string.Empty;
    public int TotalDisponibles { get; set; }
    public Dictionary<string, List<AsientoItemDto>> Filas { get; set; } = new();
}

public class BloqueoAsientoRequest
{
    public int FuncionId { get; set; }
    public int AsientoId { get; set; }
    public string CodigoAsiento { get; set; } = string.Empty;
    public string UsuarioId { get; set; } = string.Empty;
}

public class BloqueoAsientoResponse
{
    public bool Exito { get; set; }
    public string Mensaje { get; set; } = string.Empty;
    public string? CodigoAsiento { get; set; }
    public DateTime? ExpiracionUtc { get; set; }
}
