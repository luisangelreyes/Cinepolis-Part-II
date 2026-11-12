using Microsoft.AspNetCore.Mvc;
using Cinepolis.Api.Services;

namespace Cinepolis.Api.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class CarteleraController : ControllerBase
{
    private readonly ICarteleraService _carteleraService;
    private readonly ILogger<CarteleraController> _logger;

    public CarteleraController(ICarteleraService carteleraService, ILogger<CarteleraController> logger)
    {
        _carteleraService = carteleraService;
        _logger = logger;
    }

    [HttpGet("{complejoSlug}")]
    public async Task<IActionResult> GetCartelera(string complejoSlug, [FromQuery] string? fecha = null)
    {
        try
        {
            var cartelera = await _carteleraService.ObtenerCarteleraAsync(complejoSlug, fecha);
            return Ok(cartelera);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error al obtener cartelera para el complejo {Complejo}", complejoSlug);
            return StatusCode(500, new { mensaje = "Error interno al consultar la cartelera." });
        }
    }
}
