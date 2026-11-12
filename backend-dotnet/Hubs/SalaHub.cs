using Microsoft.AspNetCore.SignalR;

namespace Cinepolis.Api.Hubs;

public interface ISalaClient
{
    Task AsientoBloqueado(string codigoAsiento, string usuarioId);
    Task AsientoLiberado(string codigoAsiento);
    Task SalaActualizada(int funcionId, string mensaje);
    Task UsuarioConectado(string connectionId);
}

public class SalaHub : Hub<ISalaClient>
{
    private readonly ILogger<SalaHub> _logger;

    public SalaHub(ILogger<SalaHub> logger)
    {
        _logger = logger;
    }

    public async Task UnirseASala(int funcionId)
    {
        var groupName = $"sala_{funcionId}";
        await Groups.AddToGroupAsync(Context.ConnectionId, groupName);
        _logger.LogInformation("Cliente {ConnectionId} se unió al canal de la sala {FuncionId}", Context.ConnectionId, funcionId);
        await Clients.Caller.UsuarioConectado(Context.ConnectionId);
    }

    public async Task SalirDeSala(int funcionId)
    {
        var groupName = $"sala_{funcionId}";
        await Groups.RemoveFromGroupAsync(Context.ConnectionId, groupName);
        _logger.LogInformation("Cliente {ConnectionId} salió del canal de la sala {FuncionId}", Context.ConnectionId, funcionId);
    }

    public async Task NotificarAsientoBloqueado(int funcionId, string codigoAsiento, string usuarioId)
    {
        var groupName = $"sala_{funcionId}";
        await Clients.OthersInGroup(groupName).AsientoBloqueado(codigoAsiento, usuarioId);
    }

    public async Task NotificarAsientoLiberado(int funcionId, string codigoAsiento)
    {
        var groupName = $"sala_{funcionId}";
        await Clients.OthersInGroup(groupName).AsientoLiberado(codigoAsiento);
    }

    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        _logger.LogInformation("Cliente desconectado: {ConnectionId}", Context.ConnectionId);
        await base.OnDisconnectedAsync(exception);
    }
}

