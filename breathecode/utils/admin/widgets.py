import json
from django.contrib.admin import widgets
from django.forms import Media
from django.utils.safestring import mark_safe


class PrettyJSONWidget(widgets.AdminTextareaWidget):
    def __init__(self, attrs=None):
        default_attrs = {"class": "vLargeTextField", "rows": "20", "style": "min-width: 300px;"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
        self.help_text = attrs.get("help_text", "") if attrs else ""

    @property
    def media(self):
        return Media(
            css={
                "all": [
                    "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css",
                    "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/theme/monokai.min.css",
                ]
            },
            js=[
                "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js",
                "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/javascript/javascript.min.js",
            ],
        )

    def format_value(self, value):
        """Format the value for display in the widget"""
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                # Try to parse string as JSON and re-format it
                value = json.loads(value)
            except json.JSONDecodeError:
                return value
        return json.dumps(value, indent=4, sort_keys=True)

    def value_from_datadict(self, data, files, name):
        """Parse the JSON string value from form data"""
        value = super().value_from_datadict(data, files, name)
        if value:
            try:
                # Parse the JSON string to ensure it's valid and convert to Python object
                return json.loads(value)
            except json.JSONDecodeError:
                # Return the raw string if it's not valid JSON
                return value
        return value

    def render(self, name, value, attrs=None, renderer=None):
        formatted_value = self.format_value(value)
        textarea = super().render(name, formatted_value, attrs, renderer)
        help_text = mark_safe(self.help_text if hasattr(self, "help_text") else "")

        return mark_safe(
            f"""
        <div style="position: relative; min-width: 300px; margin-top: 20px;">
            <div class="help" style="position: absolute; top: -20px; left: 0; right: 0;
                                    font-size: 12px; color: #666;">
                {help_text}
            </div>
            {textarea}
            <div id="status_{name}" style="position: absolute; bottom: -20px; left: 0; right: 0; height: 20px;
                                         text-align: center; color: white; font-size: 12px;">
                JSON Status
            </div>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', (event) => {{
                const statusBar = document.getElementById('status_' + '{name}');
                const editor = CodeMirror.fromTextArea(document.getElementById('id_{name}'), {{
                    mode: "application/json",
                    theme: "monokai",
                    lineNumbers: true,
                    matchBrackets: true,
                    autoCloseBrackets: true,
                    indentUnit: 4,
                    height: "auto",
                    viewportMargin: Infinity,
                    tabSize: 4,
                    foldGutter: true,
                    gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"],
                    extraKeys: {{"Ctrl-Q": function(cm){{ cm.foldCode(cm.getCursor()); }}}},
                    lint: true,
                }});

                // Set minimum width for the editor
                editor.getWrapperElement().style.minWidth = '300px';

                // Function to validate JSON
                const validateJSON = (text) => {{
                    try {{
                        JSON.parse(text);
                        statusBar.style.backgroundColor = '#28a745';
                        statusBar.textContent = 'Valid JSON';
                        return true;
                    }} catch (e) {{
                        statusBar.style.backgroundColor = '#dc3545';
                        statusBar.textContent = 'Invalid JSON: ' + e.message;
                        return false;
                    }}
                }};

                // Initial validation
                validateJSON(editor.getValue());

                // Validate on change
                editor.on('change', (cm) => {{
                    validateJSON(cm.getValue());
                }});
            }});
        </script>
        """
        )
