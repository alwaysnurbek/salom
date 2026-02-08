from datetime import timedelta

def format_time_taken(seconds):
    return str(timedelta(seconds=seconds))

def generate_leaderboard_html(test_title, submissions):
    """
    Generates a simple HTML table for the leaderboard.
    submissions: list of dict-like objects (from db query)
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Leaderboard: {test_title}</title>
        <style>
            body {{ font-family: sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h2>Leaderboard: {test_title}</h2>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Name</th>
                    <th>User</th>
                    <th>Correct</th>
                    <th>Wrong</th>
                    <th>Percent</th>
                    <th>Time</th>
                    <th>Submitted At</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for idx, sub in enumerate(submissions, 1):
        # sub keys: full_name, username, correct_count, wrong_count, percent, time_taken_seconds, submitted_at
        user_display = f"@{sub['username']}" if sub['username'] else "N/A"
        time_display = format_time_taken(sub['time_taken_seconds'] or 0)
        
        html += f"""
            <tr>
                <td>{idx}</td>
                <td>{sub['full_name']}</td>
                <td>{user_display}</td>
                <td>{sub['correct_count']}</td>
                <td>{sub['wrong_count']}</td>
                <td>{sub['percent']}%</td>
                <td>{time_display}</td>
                <td>{sub['submitted_at']}</td>
            </tr>
        """
        
    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return html
