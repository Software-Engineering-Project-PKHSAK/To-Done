from pdoc.cli import *

OUTPUT_DIR = "./docs"

# Programmatically provide settings module
SETTINGS_MODULE = "smarttodo.settings"
os.environ.setdefault('DJANGO_SETTINGS_MODULE', SETTINGS_MODULE)

# Setup Django
import django

django.setup()

cmdline_args = ["--html", "-o", OUTPUT_DIR
                , "todo.apps", "todo.forms"
                , "todo.migrations", "todo.models"
                , "todo.tests", "todo.views"]

if __name__ == "__main__":
    main(parser.parse_args(cmdline_args))
