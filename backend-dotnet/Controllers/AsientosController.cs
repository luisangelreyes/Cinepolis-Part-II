using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using Cinepolis.Api.Hubs;
using Cinepolis.Api.Models;
using Cinepolis.Api.Services;

namespace Cinepolis.Api.Controllers;

[ApiController]
[Route("api/v1/[controller]")]
public class AsientosController : ControllerBase
{
    private readonly ICarteleraService _carteleraService;
    private readonly IHubContext<SalaHub, ISalaClient> _salaHub;
    private readonly ILogger<AsientosController> _logger;

    public AsientosController(
        ICarteleraService carteleraService, 
        IHubContext<SalaHub, ISalaClient> salaHub,
        ILogger<AsientosController> logger)
    {
        _carteleraService = carteleraService;
        _salaHub = salaHub;
        _logger = logger;
    }

    [HttpGet("funcion/{funcionId:int}")]
    public async Task<IActionResult> GetMapaSala(int funcionId)
    {
        try
        {
            var mapa = await _carteleraService.ObtenerMapaSalaAsync(funcionId);
            if (mapa == null)
            {
                return NotFound(new { mensaje = $"No se encontró la función con ID {funcionId}." });
            }
            return Ok(mapa);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error al consultar mapa de asientos para la función {FuncionId}", funcionId);
            return StatusCode(500, new { mensaje = "Error interno al consultar asientos." });
        }
    }

    [HttpPost("bloquear")]
    public async Task<IActionResult> BloquearAsiento([FromBody] BloqueoAsientoRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.CodigoAsiento) || request.FuncionId <= 0)
        {
            return BadRequest(new { mensaje = "Datos de bloqueo inválidos." });
        }

        // Emitir notificación en tiempo real a todos los clientes de la misma sala vía SignalR
        var groupName = $"sala_{request.FuncionId}";
        await _salaHub.Clients.Group(groupName).AsientoBloqueado(request.CodigoAsiento, request.UsuarioId);

        _logger.LogInformation("Asiento {Codigo} bloqueado temporalmente en función {FuncionId}", request.CodigoAsiento, request.FuncionId);

        return Ok(new BloqueoAsientoResponse
        {
            Exito = true,
            Mensaje = $"Asiento {request.CodigoAsiento} bloqueado temporalmente.",
            CodigoAsiento = request.CodigoAsiento,
            ExpiracionUtc = DateTime.UtcNow.AddMinutes(10)
        });
    }

    [HttpPost("liberar")]
    public async Task<IActionResult> LiberarAsiento([FromBody] BloqueoAsientoRequest request)
    {
        var groupName = $"sala_{request.FuncionId}";
        await _salaHub.Clients.Group(groupName).AsientoLiberado(request.CodigoAsiento);

        _logger.LogInformation("Asiento {Codigo} liberado en función {FuncionId}", request.CodigoAsiento, request.FuncionId);

        return Ok(new { exito = true, mensaje = $"Asiento {request.CodigoAsiento} liberado." });
    }
}

