using Microsoft.AspNetCore.Mvc;
using Cinepolis.Api.Services;

namespace Cinepolis.Api.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class PeliculasController : ControllerBase
{
    private readonly ICarteleraService _carteleraService;
    private readonly ILogger<PeliculasController> _logger;

    public PeliculasController(ICarteleraService carteleraService, ILogger<PeliculasController> logger)
    {
        _carteleraService = carteleraService;
        _logger = logger;
    }

    [HttpGet("{id:int}")]
    public async Task<IActionResult> GetPelicula(int id)
    {
        try
        {
            var pelicula = await _carteleraService.ObtenerPeliculaAsync(id);
            if (pelicula == null)
            {
                return NotFound(new { mensaje = $"No se encontró la película con ID {id}." });
            }
            return Ok(pelicula);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error al consultar película {PeliculaId}", id);
            return StatusCode(500, new { mensaje = "Error interno al consultar la película." });
        }
    }
}

