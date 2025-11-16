#!/bin/bash

unset http_proxy
unset https_proxy

# Colores (por si quieres mantenerlos en consola, pero en los reportes quedan planos)
ROJO='\E[31;40m'
VERDE='\E[32;40m'
NORMAL='\E[0m'
CYAN='\E[36;40m'

# Carpeta de reportes
DIR_REPORTE="/home/jboss/reportes-kieservers"

# URLs de los servidores y archivos de salida
declare -A SERVIDORES=(
    ["kieserver-01"]="http://decision-manager-prod-01-fms-faultmanager-prod.apps.ocp4-ph.cloudteco.com.ar/fms-rules-executor/api/rest/event/groupCount"
    ["kieserver-02"]="http://decision-manager-prod-02-fms-faultmanager-prod.apps.ocp4-ph.cloudteco.com.ar/fms-rules-executor/api/rest/event/groupCount"
    ["kieserver-03"]="http://decision-manager-prod-03-fms-faultmanager-prod.apps.ocp4-ph.cloudteco.com.ar/fms-rules-executor/api/rest/event/groupCount"
    ["kieserver-04"]="http://decision-manager-prod-04-fms-faultmanager-prod.apps.ocp4-ph.cloudteco.com.ar/fms-rules-executor/api/rest/event/groupCount"
    ["kieserver-05"]="http://decision-manager-prod-05-fms-faultmanager-prod.apps.ocp4-ph.cloudteco.com.ar/fms-rules-executor/api/rest/event/groupCount"
    ["kieserver-06"]="http://decision-manager-prod-06-fms-faultmanager-prod.apps.ocp4-ph.cloudteco.com.ar/fms-rules-executor/api/rest/event/groupCount"
)

# Función para procesar JSON con tr y sed
procesar_json_tr_sed() {
    local url=$1
    local servidor=$2
    local tmpfile="/tmp/${servidor}.json"
    local reporte="${DIR_REPORTE}/reporte_${servidor}.txt"

    # Ejecutar curl
    curl -s "$url" > "$tmpfile"

    # Escribir reporte (append, no sobrescribir)
    {
        echo -e "-----------------------------------------------------"
        echo "$servidor - Hora: $(date '+%Y-%m-%d %H:%M:%S')"
        echo -e "-----------------------------------------------------"
        tr '{},' '\n' < "$tmpfile" | sed 's/"//g' | grep -E 'Fall|Event|Flapping|NetworkElement|Notification'
        echo
    } >> "$reporte"
}


# Procesar todos los servidores
for srv in "${!SERVIDORES[@]}"; do
    procesar_json_tr_sed "${SERVIDORES[$srv]}" "$srv"
done

