def up(app):
  from flask import Flask, request, jsonify
  import os
  import shutil
  from urllib.parse import unquote, quote

  # PATH เป้าหมายแต่ละคอลัมน์
  import os

  BASE_DIR = os.path.dirname(os.path.abspath(__file__))
  
  TARGET_PATHS = {
      "1": os.path.join(BASE_DIR, ""),                 # root ของโปรเจกต์
      "2": os.path.join(BASE_DIR, "problems"),         # โฟลเดอร์ problems
      "3": os.path.join(BASE_DIR, "templates")         # โฟลเดอร์ templates
  }


  @app.route('/upcode')
  def index():
      paths = {
          "1": request.args.get('p1', ''),
          "2": request.args.get('p2', ''),
          "3": request.args.get('p3', '')
      }

      columns_html = ''

      for key, base_path in TARGET_PATHS.items():
          rel_path = paths.get(key, '')
          safe_rel_path = os.path.normpath(unquote(rel_path)).replace("\\", "/")
          if safe_rel_path.startswith(".."):
              safe_rel_path = ""
          abs_path = os.path.join(base_path, safe_rel_path)
          if not os.path.isdir(abs_path):
              abs_path = base_path
              safe_rel_path = ""

          try:
              items = []
              with os.scandir(abs_path) as it:
                  for entry in sorted(it, key=lambda e: (not e.is_dir(), e.name.lower())):
                      items.append({
                          "name": entry.name,
                          "type": "folder" if entry.is_dir() else "file"
                      })
          except Exception as e:
              items = [{"name": f"Error: {str(e)}", "type": "file"}]

          file_list_html = '<ul style="list-style:none; padding-left:10px;">'
          for item in items:
              icon = "📁" if item["type"] == "folder" else "📄"
              if item["type"] == "folder":
                  new_path = os.path.join(safe_rel_path, item["name"]) if safe_rel_path else item["name"]
                  new_path_enc = quote(new_path)
                  link = f'?p{key}={new_path_enc}'
                  delete_button = f'''
                      <button class="delete-button" onclick="deleteFolder('{new_path_enc}')">DEL</button>
                  ''' if key == "2" else ''
                  file_list_html += f'<li style="margin-bottom:4px;">{icon} <a href="{link}">{item["name"]}</a>{delete_button}</li>'
              else:
                  file_list_html += f'<li style="margin-bottom:4px;">{icon} {item["name"]}</li>'
          file_list_html += '</ul>'

          path_parts = safe_rel_path.split('/') if safe_rel_path else []
          accum_path = ''
          breadcrumbs = [f'<a href="/upcode?p{key}=">/{os.path.basename(base_path)}</a>']
          for part in path_parts:
              accum_path = os.path.join(accum_path, part) if accum_path else part
              accum_path_enc = quote(accum_path)
              breadcrumbs.append(f'<a href="/upcode?p{key}={accum_path_enc}">{part}</a>')
          breadcrumb_html = ' / '.join(breadcrumbs)

          columns_html += f'''
          <div class="column">
              <h3>Target {key}: {base_path}</h3>
              <div class="breadcrumbs">{breadcrumb_html}</div>
              <div class="files-list">{file_list_html}</div>
          </div>
          '''

      return f'''
  <!DOCTYPE html>
  <html>
  <head>
  <meta charset="utf-8" />
  <title>3 Column Explorer + Upload</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background:#f0f2f5;
      padding: 20px;
      margin: 0;
    }}
    .container {{
      display: flex;
      gap: 20px;
      justify-content: space-between;
      margin-bottom: 30px;
    }}
    .column {{
      background: white;
      padding: 15px;
      border-radius: 10px;
      box-shadow: 0 0 8px rgba(0,0,0,0.1);
      flex: 1;
      min-width: 300px;
      max-height: 500px;
      overflow-y: auto;
    }}
    h2 {{
      text-align: center;
      margin-top: 10px;
      margin-bottom: 30px;
    }}
    h3 {{
      margin-top: 0;
    }}
    ul {{
      list-style: none;
      padding-left: 10px;
    }}
    li {{
      margin-bottom: 6px;
    }}
    a {{
      text-decoration: none;
      color: #0366d6;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .breadcrumbs {{
      font-size: 0.9em;
      margin-bottom: 10px;
    }}
    .breadcrumbs a {{
      color: #555;
    }}
    .upload-section {{
      text-align: center;
      background: white;
      padding: 20px;
      border-radius: 10px;
      box-shadow: 0 0 8px rgba(0,0,0,0.1);
      width: 600px;
      margin: 0 auto;
    }}
    label {{
      font-weight: bold;
      margin-top: 15px;
      display: block;
      text-align: left;
    }}
    input[type=file], select {{
      margin-top: 5px;
      width: 100%;
      padding: 8px;
      font-size: 14px;
      border-radius: 6px;
      border: 1px solid #ccc;
    }}
    button {{
      margin-top: 15px;
      background: #28a745;
      border: none;
      color: white;
      padding: 10px 20px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
      font-size: 14px;
    }}
    button:hover {{
      background: #218838;
    }}
    .delete-button {{
      margin-left: 10px;
      background: #dc3545;
      border: none;
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      cursor: pointer;
    }}
    .delete-button:hover {{
      background: #c82333;
    }}
    #result {{
      margin-top: 15px;
      font-weight: bold;
      text-align: center;
    }}
  </style>
  </head>
  <body>

  <h2>📁 Upload Folder</h2>

  <div class="container">
    {columns_html}
  </div>

  <div class="upload-section">
    <form id="uploadForm" enctype="multipart/form-data">
      <label>Select folder to upload:</label>
      <input type="file" id="folderInput" name="files[]" webkitdirectory directory multiple required>

      <label>Select target folder:</label>
      <select name="target_folder" required>
        <option value="1">/home/maybe/TOI_Zero/</option>
        <option value="2">/home/maybe/TOI_Zero/problems</option>
        <option value="3">/home/maybe/TOI_Zero/templates</option>
      </select>

      <button type="submit">🚀 Upload Folder</button>
    </form>

    <div id="result"></div>
  </div>

  <script>
  document.getElementById('uploadForm').addEventListener('submit', function(e){{
    e.preventDefault();
    const form = e.target;
    const formData = new FormData();
    const files = document.getElementById('folderInput').files;
    if(files.length === 0){{
      alert('Please select folder to upload.');
      return;
    }}
    for(let i=0; i<files.length; i++){{
      formData.append('files[]', files[i], files[i].webkitRelativePath);
    }}
    const targetFolder = form.target_folder.value;
    formData.append('target_folder', targetFolder);
    fetch('/upload', {{
      method: 'POST',
      body: formData
    }}).then(res => res.json())
      .then(data => {{
        const result = document.getElementById('result');
        result.style.color = data.status === "success" ? 'green' : 'red';
        result.textContent = data.message;
      }})
      .catch(() => {{
        document.getElementById('result').textContent = '❌ Upload failed.';
      }});
  }});

  function deleteFolder(folderPath) {{
    const password = prompt("Enter password to delete this folder:");
    if (!password) return;
    fetch('/delete_folder', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ folder_path: folderPath, target_id: "2", password: password }})
    }})
    .then(res => res.json())
    .then(data => {{
      alert(data.message);
      if (data.status === "success") location.reload();
    }})
    .catch(err => {{
      alert("❌ Error deleting folder.");
    }});
  }}
  </script>

  </body>
  </html>
  '''

  @app.route('/upload', methods=['POST'])
  def upload():
      selected = request.form.get("target_folder")
      target_dir = TARGET_PATHS.get(selected)
      if not target_dir:
          return jsonify({"status": "error", "message": "Invalid target folder."}), 400

      files = request.files.getlist('files[]')
      if not files:
          return jsonify({"status": "error", "message": "No files uploaded."}), 400

      try:
          for file in files:
              rel_path = file.filename
              if ".." in rel_path or rel_path.startswith("/") or rel_path.startswith("\\"):
                  return jsonify({"status": "error", "message": "Invalid file path."}), 400
              full_path = os.path.abspath(os.path.join(target_dir, rel_path))
              if not full_path.startswith(os.path.abspath(target_dir)):
                  return jsonify({"status": "error", "message": "Unsafe path."}), 400
              os.makedirs(os.path.dirname(full_path), exist_ok=True)
              file.save(full_path)
          return jsonify({"status": "success", "message": f"Uploaded {len(files)} files to {target_dir}."})
      except Exception as e:
          return jsonify({"status": "error", "message": str(e)}), 500

  @app.route('/delete_folder', methods=['POST'])
  def delete_folder():
      data = request.get_json()
      folder_path = unquote(data.get('folder_path', ''))
      target_id = data.get('target_id')
      password = data.get('password', '')
      CORRECT_PASSWORD = "1234"

      if password != CORRECT_PASSWORD:
          return jsonify({"status": "error", "message": "Incorrect password."}), 403

      target_base = TARGET_PATHS.get(target_id)
      if not target_base:
          return jsonify({"status": "error", "message": "Invalid target ID."}), 400

      abs_path = os.path.abspath(os.path.join(target_base, folder_path))
      if not abs_path.startswith(os.path.abspath(target_base)) or not os.path.isdir(abs_path):
          return jsonify({"status": "error", "message": "Invalid or missing folder."}), 400

      try:
          shutil.rmtree(abs_path)
          return jsonify({"status": "success", "message": f"Deleted folder '{folder_path}'."})
      except Exception as e:
          return jsonify({"status": "error", "message": f"Failed to delete: {str(e)}"}), 500

  # สร้างโฟลเดอร์เป้าหมายถ้ายังไม่มี
  for path in TARGET_PATHS.values():
      os.makedirs(path, exist_ok=True)
