#!/bin/zsh
# GHOST-HEALER v2.0: Sovereign Auto-Dismiss & Allow Daemon
# - No roba el foco (silencioso).
# - Rendimiento instantáneo mediante inyección JS para el DOM.
# - Captura popups nativos de permisos en macOS.

echo "[+] Iniciando GHOST-HEALER v2.0..."
echo "[+] Monitoreando web (Chrome) y popups del sistema en segundo plano..."
echo "[!] Nota: En Chrome, asegúrate de activar View > Developer > Allow JavaScript from Apple Events"

while true; do
  osascript <<EOF > /dev/null 2>&1
    -- 1. CORTA EL BLOQUEO WEB (Inyección de JS en Chrome)
    -- Evita el uso de 'entire contents' en accesibilidad que dispara la CPU al 100%
    try
        tell application "Google Chrome"
            if exists (active tab of window 1) then
                execute javascript "
                    (function() {
                        const buttons = Array.from(document.querySelectorAll('button, div[role=\"button\"]'));
                        const target = buttons.find(b => {
                            const txt = (b.textContent || '').toLowerCase();
                            return txt.includes('dismiss') || txt.includes('allow') || txt.includes('permitir') || txt.includes('try again');
                        });
                        if (target) {
                            console.log('[GHOST-HEALER] Clicked:', target.textContent);
                            target.click();
                        }
                    })();
                " on active tab of window 1
            end if
        end tell
    end try

    -- 2. POPUPS NATIVOS DE MACOS (SecurityAgent y App Activa)
    -- Para ventanas de tipo "Terminal quiere acceder a la carpeta X -> Permitir"
    try
        tell application "System Events"
            set fgApp to first application process whose frontmost is true
            tell fgApp
                if exists (window 1) then
                    tell window 1
                        -- Botones directos en la ventana
                        if exists (button "Allow") then click button "Allow"
                        if exists (button "Permitir") then click button "Permitir"
                        if exists (button "OK") then click button "OK"
                        
                        -- Si el popup es un "Sheet" (alerta desplegable desde la barra superior)
                        if exists (sheet 1) then
                            tell sheet 1
                                if exists (button "Allow") then click button "Allow"
                                if exists (button "Permitir") then click button "Permitir"
                            end tell
                        end if
                    end tell
                end if
            end tell
            
            -- Monitoreo específico de alertas del sistema (CoreServicesUIAgent / SecurityAgent)
            if exists (process "SecurityAgent") then
                tell process "SecurityAgent"
                    if exists (window 1) then
                        if exists (button "Allow" of window 1) then click button "Allow" of window 1
                        if exists (button "Permitir" of window 1) then click button "Permitir" of window 1
                    end if
                end tell
            end if
        end tell
    end try
EOF

  sleep 3
done
