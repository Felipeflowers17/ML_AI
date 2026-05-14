#!/usr/bin/env python3
"""Helper para arrancar la aplicación Monitor de Licitaciones."""
import sys
import os

# Asegurar que src está en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

from monitor_licitaciones.main import main
main()