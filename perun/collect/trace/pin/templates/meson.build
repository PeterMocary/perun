perun_collect_trace_pin_templates_dir = perun_collect_trace_pin_dir / 'templates'

perun_collect_trace_pin_templates_files = files(
    'analysis-functions.jinja2',
    'data-structures.jinja2',
    'instrumentation-functions.jinja2',
    'main-function.jinja2',
    'makefile.jinja2',
    'pintool.jinja2',
    'pintool-duration.jinja2',
    'pintool-memory.jinja2',
)

py3.install_sources(
    perun_collect_trace_pin_templates_files,
    subdir: perun_collect_trace_pin_templates_dir,
)