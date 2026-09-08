# Script de Validação do Rate Limiting no Artfolio (FastAPI + SlowAPI + Redis)
$url = "http://127.0.0.1:8000/auth/login"
$body = '{"email": "ratelimit_ps@artfolio.com", "senha": "qualquersenha123"}'

Write-Host "=== Iniciando disparo de 6 requisicoes consecutivas para $url ===" -ForegroundColor Cyan

1..6 | ForEach-Object {
    $i = $_
    try {
        $response = Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json"
        Write-Host "Requisicao $i : Sucesso (200 OK)" -ForegroundColor Green
    }
    catch {
        $status = 0
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        $respBody = ""
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            $respBody = $_.ErrorDetails.Message
        } elseif ($_.Exception.Response) {
            try {
                $stream = $_.Exception.Response.GetResponseStream()
                $reader = New-Object System.IO.StreamReader($stream)
                $respBody = $reader.ReadToEnd()
            } catch {}
        }

        if ($status -eq 429) {
            Write-Host "Requisicao $i : [BLOQUEADO 429] -> $respBody" -ForegroundColor Red
        } else {
            Write-Host "Requisicao $i : Status $status -> $respBody" -ForegroundColor Yellow
        }
    }
}
