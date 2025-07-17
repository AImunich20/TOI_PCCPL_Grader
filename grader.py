import subprocess
import os
import time
import json
import psutil
import pandas as pd


def get_problem_list():
    return [d for d in os.listdir('problems') if os.path.isdir(os.path.join('problems', d))]


def run_grader(problem, code_path):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    problem_dir = os.path.join(BASE_DIR, 'problems', problem)
    with open(os.path.join(problem_dir, 'config.json')) as f:
        config = json.load(f)
    testcase_path = os.path.join(problem_dir, 'testcase.csv')
    if not os.path.exists(testcase_path):
        return 'Error: testcase.csv not found', 0, []
    testcases = pd.read_csv(testcase_path)
    exe_file = code_path.replace('.cpp', '.out').replace('.c', '.out')
    tmp_output = 'user_output.txt'
    compile_cmd = ['g++' if code_path.endswith('.cpp') else 'gcc', code_path, '-o', exe_file]
    compile = subprocess.run(compile_cmd, capture_output=True, text=True)

    if compile.returncode != 0:
        return f'Compile Error\n{compile.stderr}', 0, []

    result_detail = []
    total_score = 0

    for idx, row in testcases.iterrows():
        case_name = row['name']
        input_data = str(row['input'])
        expected_output = str(row['output']).strip()
        case_score = int(row['score'])

        try:
            with open('temp_input.txt', 'w') as infile:
                infile.write(input_data)
            with open('temp_input.txt') as infile, open(tmp_output, 'w') as outfile:
                start = time.time()
                process = subprocess.Popen([exe_file],
                                           stdin=infile,
                                           stdout=outfile,
                                           stderr=subprocess.PIPE)
                pid = process.pid
                p = psutil.Process(pid)
                time_limit = config.get('time_limit', 2)
                memory_limit = config.get('memory_limit', 256)

                while process.poll() is None:
                    mem = p.memory_info().rss / (1024 * 1024)  # MB
                    if mem > memory_limit:
                        process.kill()
                        result = 'Memory Limit Exceeded'
                        score = 0
                        break
                    if time.time() - start > time_limit:
                        process.kill()
                        result = 'Time Limit Exceeded'
                        score = 0
                        break
                    time.sleep(0.01)
                else:
                    if process.returncode != 0:
                        result = 'Runtime Error'
                        score = 0
                    else:
                        with open(tmp_output) as user_out:
                            user_output = user_out.read().strip()
                            expected_tokens = expected_output.split()
                            user_tokens = user_output.split()

                            if expected_tokens == user_tokens:
                                result = 'Passed'
                                score = case_score
                            else:
                                result = 'Output incorrect'
                                score = 0

        except Exception as e:
            result = f'Error: {e}'
            score = 0

        result_detail.append({
            'Testcase': case_name,
            'Result': result,
            'Score': score
        })

        total_score += score
    for temp_file in [exe_file, tmp_output, 'temp_input.txt']:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    summary_lines = [f"{d['Testcase']}: {d['Result']} ({d['Score']} pts)" for d in result_detail]
    result_text = f"Total Score: {total_score}\n\n" + "\n".join(summary_lines)

    return result_text, total_score, result_detail
