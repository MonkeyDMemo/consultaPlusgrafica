import azure.functions as func

# Registrar la función
app = func.FunctionApp()

@app.function_name(name="consultaplus")
@app.route(route="consultaplus", auth_level=func.AuthLevel.ANONYMOUS)
def upload_log(req: func.HttpRequest) -> func.HttpResponse:
    import consultaplus.v2 as function_logic
    return function_logic.main(req)