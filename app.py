from flask import g,Flask, render_template, request, redirect, session, url_for, get_flashed_messages, flash, send_from_directory, jsonify
import time
import os
import pandas as pd
from door import run_terminal
from grader import run_grader, get_problem_list
from datetime import datetime, timedelta
import threading
import shutil
from up import up

app = Flask(__name__)
app.secret_key = 'supersecretkey'
run_terminal(app)
up(app)

PROBLEM_DIR = 'problems'
SUBMISSION_DIR = 'submissions'

server_start_time = datetime.now()
server_duration = timedelta(hours=1)
server_end_time = server_start_time + server_duration

# เก็บ log ทั้งหมดในหน่วยความจำ
REQUEST_LOG = []

@app.before_request
def track_every_request():
    if "client_id" not in session:
        session["client_id"] = str(uuid.uuid4())[:8]

    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": request.remote_addr,
        "path": request.path,
        "method": request.method,
        "client_id": session["client_id"]
    }

    # เพิ่มลง list
    REQUEST_LOG.append(log_entry)

    # (Optional) บันทึกลงไฟล์
    with open("request_tracking.log", "a") as f:
        f.write(f"{log_entry['timestamp']} - {log_entry['client_id']} - {log_entry['ip']} {log_entry['method']} {log_entry['path']}\n")

@app.route('/submissions/<user>/CODE/<filename>')
def download_submission(user, filename):
    return send_from_directory(f'submissions/{user}/CODE', filename, as_attachment=True)

def safe_save_csv(df, path):
    backup_dir = 'leader_Back'
    os.makedirs(backup_dir, exist_ok=True)

    if os.path.exists(path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.basename(path)
        backup_path = os.path.join(backup_dir, f"{filename}.{timestamp}.bak")
        shutil.copy(path, backup_path)

        # ลบไฟล์เก่าใน leader_Back ให้เหลือแค่ 10 ไฟล์ล่าสุดเท่านั้น
        backup_files = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith(filename)],
            key=lambda x: os.path.getmtime(os.path.join(backup_dir, x))
        )

        while len(backup_files) > 10:
            oldest = backup_files.pop(0)
            os.remove(os.path.join(backup_dir, oldest))

    df.to_csv(path, index=False)



@app.route('/leaderboard')
def leaderboard():
    leaderboard_path = 'leaderboard.csv'
    if os.path.exists(leaderboard_path):
        df = pd.read_csv(leaderboard_path, dtype={'user': str})
        required_cols = ['user', 'name', 'Total']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''
        df = df.sort_values(by='Total', ascending=False)
        leaderboard_list = df[['user', 'name', 'Total']].to_dict(orient='records')
    else:
        leaderboard_list = []

    time_left = max(int((server_end_time - datetime.now()).total_seconds()), 0)

    return render_template('leaderboard.html',
                           leaderboard=leaderboard_list,
                           server_start_time=server_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                           time_left_seconds=time_left)


@app.route('/api/leaderboard')
def api_leaderboard():
    leaderboard_path = 'leaderboard.csv'
    if not os.path.exists(leaderboard_path) or os.stat(leaderboard_path).st_size == 0:
        return jsonify([])

    try:
        df = pd.read_csv(leaderboard_path, dtype={'user': str})
        required_cols = ['user', 'name', 'Total']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''
        df = df.sort_values(by='Total', ascending=False)
        leaderboard_list = df[required_cols].to_dict(orient='records')
        return jsonify(leaderboard_list)
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify([])


@app.route('/problems/<problem_id>/<filename>')
def serve_problem_file(problem_id, filename):
    return send_from_directory(f'{PROBLEM_DIR}/{problem_id}', filename)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = str(request.form.get('FirstName', '')).strip()
        last_name = str(request.form.get('LastName', '')).strip()
        class_name = str(request.form.get('Class', '')).strip()
        raw_id = str(request.form.get('StudentID', '')).strip()
        student_id = f"A{raw_id.lstrip('A')}"
        phone = str(request.form.get('Phone', '')).strip()

        users_csv = 'users.csv'
        if os.path.exists(users_csv):
            users_df = pd.read_csv(users_csv, dtype=str)
            if student_id in users_df['StudentID'].astype(str).values:
                flash("StudentID นี้มีอยู่แล้ว กรุณาใช้รหัสอื่น")
                return redirect(url_for('signup'))
        else:
            users_df = pd.DataFrame(columns=['FirstName', 'LastName', 'Class', 'StudentID', 'Phone'])

        new_user = {
            'FirstName': first_name,
            'LastName': last_name,
            'Class': class_name,
            'StudentID': student_id,
            'Phone': phone
        }
        users_df = pd.concat([users_df, pd.DataFrame([new_user])], ignore_index=True)
        safe_save_csv(users_df, users_csv)

        user_path = os.path.join(SUBMISSION_DIR, student_id)
        os.makedirs(os.path.join(user_path, 'CODE'), exist_ok=True)
        os.makedirs(os.path.join(user_path, 'Detail'), exist_ok=True)

        score_csv_path = os.path.join(user_path, 'score.csv')
        if not os.path.exists(score_csv_path):
            safe_save_csv(pd.DataFrame(columns=['Problem', 'Score', 'Attempt']), score_csv_path)

        u_leaderboard_path = os.path.join(user_path, 'U_leaderboard.csv')
        if not os.path.exists(u_leaderboard_path):
            problem_list = get_problem_list()
            scores = {problem: 0 for problem in problem_list}
            scores['Total'] = 0
            u_df = pd.DataFrame([scores])
            u_df['Total'] = u_df[problem_list].sum(axis=1)
            safe_save_csv(u_df, u_leaderboard_path)

        leaderboard_csv = 'leaderboard.csv'
        leaderboard_entry = {
            'user': student_id,
            'name': f"{first_name} {last_name}",
            'Total': 0
        }
        if os.path.exists(leaderboard_csv):
            lb_df = pd.read_csv(leaderboard_csv, dtype={'user': str})
            if student_id not in lb_df['user'].values:
                lb_df = pd.concat([lb_df, pd.DataFrame([leaderboard_entry])], ignore_index=True)
                safe_save_csv(lb_df, leaderboard_csv)
        else:
            lb_df = pd.DataFrame([leaderboard_entry])
            safe_save_csv(lb_df, leaderboard_csv)

        session['user'] = student_id
        session['name'] = f"{first_name} {last_name}"
        flash("สมัครสมาชิกสำเร็จ! เข้าสู่ระบบได้เลย")
        return redirect(url_for('submit'))

    return render_template('Signup.html')


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form['username']
        user_path = os.path.join(SUBMISSION_DIR, student_id)
        if not os.path.exists(user_path):
            flash("ไม่พบรหัสนักเรียนนี้ กรุณาสมัครสมาชิกก่อน")
            return redirect(url_for('signup'))

        leaderboard_path = 'leaderboard.csv'
        user_name = ''
        if os.path.exists(leaderboard_path):
            df = pd.read_csv(leaderboard_path)
            user_row = df[df['user'] == student_id]
            if not user_row.empty:
                user_name = user_row.iloc[0]['name']

        session['user'] = student_id
        session['name'] = user_name
        return redirect(url_for('submit'))

    return render_template('Login.html')


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = session['user']
    user_name = session.get('name', '')
    user_path = os.path.join(SUBMISSION_DIR, user)
    os.makedirs(os.path.join(user_path, 'CODE'), exist_ok=True)

    problems = get_problem_list()
    problems = get_problems_sorted_new_to_old()
    message = None
    
    score_csv_path = os.path.join(user_path, 'score.csv')
    if os.path.exists(score_csv_path):
        score_df = pd.read_csv(score_csv_path)
    else:
        score_df = pd.DataFrame(columns=['Problem', 'Score', 'Attempt'])

    if request.method == 'POST':
        problem = request.form.get('problem')
        codefile = request.files.get('codefile')

        if not problem or problem not in problems:
            message = "Invalid problem selected."
        elif not codefile:
            message = "No code file uploaded."
        else:
            # filename = codefile.filename
            # save_path = os.path.join(user_path, 'CODE', filename)
            # codefile.save(save_path)

            original_ext = os.path.splitext(codefile.filename)[1] or ".txt"

            # คำนวณ attempt ล่าสุดจาก score_df
            attempts = score_df[score_df['Problem'] == problem]['Attempt']
            attempt = int(attempts.max() + 1) if not attempts.empty else 1

            # ตั้งชื่อไฟล์ เช่น Task1_1.cpp
            filename = f"{problem}_{attempt}{original_ext}"
            save_path = os.path.join(user_path, 'CODE', filename)

            # บันทึกไฟล์
            codefile.save(save_path)

            result_text, total_score, details = run_grader(problem, save_path)

            # สร้างโฟลเดอร์ Detail ถ้ายังไม่มี
            detail_path = os.path.join(user_path, 'Detail')
            os.makedirs(detail_path, exist_ok=True)

            # ตั้งชื่อไฟล์สำหรับรายละเอียด เช่น Task1_1.txt
            detail_filename = f"{problem}_{attempt}.txt"
            detail_file_path = os.path.join(detail_path, detail_filename)

            # บันทึกรายละเอียดของผลลัพธ์จาก grader
            with open(detail_file_path, 'w') as f:
                if isinstance(details, list):
                    for line in details:
                        f.write(f"{line}\n")
                elif isinstance(details, str):
                    f.write(details)
                else:
                    f.write("No detailed result provided.")

            attempts = score_df[score_df['Problem'] == problem]['Attempt']
            attempt = attempts.max() + 1 if not attempts.empty else 1
            new_row = pd.DataFrame([{'Problem': problem, 'Score': total_score, 'Attempt': attempt}])
            score_df = pd.concat([score_df, new_row], ignore_index=True)
            safe_save_csv(score_df, score_csv_path)

            u_leaderboard_path = os.path.join(user_path, 'U_leaderboard.csv')
            if os.path.exists(u_leaderboard_path):
                u_df = pd.read_csv(u_leaderboard_path)
            else:
                u_df = pd.DataFrame(columns=[*problems, 'Total'])
                u_df.loc[0] = [0]*len(problems) + [0]

            for p in problems:
                if p not in u_df.columns:
                    u_df[p] = 0

            best_scores = score_df.groupby('Problem')['Score'].max()
            for p in problems:
                u_df.at[0, p] = best_scores.get(p, 0)

            u_df['Total'] = u_df[problems].sum(axis=1)
            safe_save_csv(u_df, u_leaderboard_path)

            leaderboard_path = 'leaderboard.csv'
            if os.path.exists(leaderboard_path):
                leaderboard_df = pd.read_csv(leaderboard_path, dtype={'user': str})
            else:
                leaderboard_df = pd.DataFrame(columns=['user', 'name', *problems, 'Total'])

            for p in problems:
                if p not in leaderboard_df.columns:
                    leaderboard_df[p] = 0
            if 'Total' not in leaderboard_df.columns:
                leaderboard_df['Total'] = 0

            user_score_df = pd.read_csv(u_leaderboard_path)
            user_scores = user_score_df.iloc[0].to_dict()
            row_data = {'user': user, 'name': user_name}
            for p in problems:
                row_data[p] = user_scores.get(p, 0)
            row_data['Total'] = user_scores['Total']

            if user in leaderboard_df['user'].values:
                idx = leaderboard_df[leaderboard_df['user'] == user].index[0]
                for col in ['name', *problems, 'Total']:
                    leaderboard_df.at[idx, col] = row_data.get(col, 0)
            else:
                leaderboard_df = pd.concat([leaderboard_df, pd.DataFrame([row_data])], ignore_index=True)

            leaderboard_df = leaderboard_df[['user', 'name', *problems, 'Total']]
            safe_save_csv(leaderboard_df, leaderboard_path)

            flash(f'Submission result:\n{result_text}')
            return redirect(url_for('submit'))

    score_by_problem = {}
    for p in problems:
        df_p = score_df[score_df['Problem'] == p].copy()
        df_p = df_p.sort_values(by='Attempt', ascending=False)
        score_by_problem[p] = df_p.to_dict(orient='records')

    time_left = max(int((server_end_time - datetime.now()).total_seconds()), 0)

    return render_template('submit.html',
                           message=message,
                           result=get_flashed_messages(),
                           score_by_problem=score_by_problem,
                           problems=problems,
                           server_start_time=server_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                           time_left_seconds=time_left)


def update_leaderboards_periodically():
    while True:
        try:
            problems = get_problem_list()
            leaderboard_path = 'leaderboard.csv'
            if os.path.exists(leaderboard_path):
                leaderboard_df = pd.read_csv(leaderboard_path, dtype={'user': str})
            else:
                leaderboard_df = pd.DataFrame(columns=['user', 'name', 'Total'] + problems)

            for p in problems:
                if p not in leaderboard_df.columns:
                    leaderboard_df[p] = 0

            if os.path.exists('users.csv'):
                users_df = pd.read_csv('users.csv', dtype=str)
            else:
                users_df = pd.DataFrame(columns=['StudentID', 'FirstName', 'LastName'])

            existing_users = set(leaderboard_df['user'].astype(str).values)

            for user in os.listdir(SUBMISSION_DIR):
                user_path = os.path.join(SUBMISSION_DIR, user)
                if not os.path.isdir(user_path):
                    continue

                u_leaderboard_path = os.path.join(user_path, 'U_leaderboard.csv')
                user_scores = {}
                if os.path.exists(u_leaderboard_path):
                    try:
                        u_df = pd.read_csv(u_leaderboard_path)
                        if not u_df.empty:
                            user_scores = u_df.iloc[0].to_dict()
                    except Exception as e:
                        print(f"[WARN] Read error in {u_leaderboard_path}: {e}")

                if user in existing_users:
                    idx = leaderboard_df[leaderboard_df['user'] == user].index[0]
                else:
                    row = users_df[users_df['StudentID'] == user]
                    fname = str(row.iloc[0].get('FirstName', '')).strip() if not row.empty else ''
                    lname = str(row.iloc[0].get('LastName', '')).strip() if not row.empty else ''
                    full_name = f"{fname} {lname}".strip() if fname or lname else user
                    new_row = {'user': user, 'name': full_name, 'Total': 0}
                    for p in problems:
                        new_row[p] = 0
                    leaderboard_df = pd.concat([leaderboard_df, pd.DataFrame([new_row])], ignore_index=True)
                    idx = leaderboard_df.index[-1]
                    existing_users.add(user)

                for p in problems:
                    score = int(user_scores.get(p, 0)) if p in user_scores else 0
                    leaderboard_df.at[idx, p] = score

                leaderboard_df.at[idx, 'Total'] = leaderboard_df.loc[idx, problems].sum()

            leaderboard_df = leaderboard_df[['user', 'name'] + problems + ['Total']]
            safe_save_csv(leaderboard_df, leaderboard_path)
        except Exception as e:
            print(f'[ERROR updating leaderboard] {e}')
        time.sleep(1)

def get_problems_sorted_new_to_old():
    problems = []
    base_path = PROBLEM_DIR
    # สมมติว่าแต่ละ problem คือโฟลเดอร์ใน PROBLEM_DIR
    entries = os.listdir(base_path)

    # สร้าง list ของ (problem_name, last_modified_time)
    problem_with_time = []
    for p in entries:
        full_path = os.path.join(base_path, p)
        if os.path.isdir(full_path):
            mtime = os.path.getmtime(full_path)  # เวลาแก้ไขล่าสุด (timestamp)
            problem_with_time.append((p, mtime))

    # เรียงจากใหม่ไปเก่า (mtime มากไปน้อย)
    problem_with_time.sort(key=lambda x: x[1], reverse=False)

    # ดึงชื่อ problem เท่านั้น
    problems_sorted = [p[0] for p in problem_with_time]
    return problems_sorted

@app.route('/get_detail/<problem>/<int:attempt>')
def get_detail(problem, attempt):
    if 'user' not in session:
        return "Not logged in", 403

    user = session['user']
    user_path = os.path.join(SUBMISSION_DIR, user)
    detail_file = os.path.join(user_path, 'Detail', f"{problem}_{attempt}.txt")
    
    if not os.path.exists(detail_file):
        return "No detail found.", 404

    with open(detail_file, 'r') as f:
        return f.read()

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('name', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    threading.Thread(target=update_leaderboards_periodically, daemon=True).start()
    app.run(host='0.0.0.0', port=8000, debug=True)
