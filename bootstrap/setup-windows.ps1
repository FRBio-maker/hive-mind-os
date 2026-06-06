# Thin launcher — forwards all arguments to bootstrap.py.
# Note: creating symlinks on Windows requires Developer Mode to be enabled
# (Settings > System > For Developers) or an elevated (Administrator) prompt.
# Without it, the bootstrap copies files instead of linking them.
python "$PSScriptRoot\bootstrap.py" @args
