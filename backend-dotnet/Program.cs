using Cinepolis.Api.Hubs;
using Cinepolis.Api.Services;

var builder = WebApplication.CreateBuilder(args);

// Servicios al contenedor
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// SignalR para WebSockets en tiempo real del mapa de salas
builder.Services.AddSignalR();

// Inyección de dependencias para Dapper y servicios de negocio
builder.Services.AddSingleton<IDbConnectionFactory, NpgsqlConnectionFactory>();
builder.Services.AddScoped<ICarteleraService, CarteleraService>();

// Configuración de CORS para permitir conexiones desde Angular Web & PWA
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAngularApp", policy =>
    {
        policy.WithOrigins("http://localhost:4200", "http://127.0.0.1:4200")
              .AllowAnyHeader()
              .AllowAnyMethod()
              .AllowCredentials(); // Necesario para WebSockets de SignalR
    });
});

var app = builder.Build();

// Configuración del pipeline HTTP
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "Cinépolis Vision .NET 8 API v1");
    });
}

app.UseCors("AllowAngularApp");

app.UseRouting();

// Mapeo de controladores REST
app.MapControllers();

// Mapeo del Hub de SignalR para WebSockets de salas
app.MapHub<SalaHub>("/hub/sala");

// Endpoint de verificación de salud
app.MapGet("/", () => Results.Ok(new 
{ 
    sistema = "Cinépolis Vision Core API (.NET 8)", 
    estado = "Operativo", 
    tiempo_real = "SignalR Active", 
    version = "1.0.0" 
}));

app.Run();
