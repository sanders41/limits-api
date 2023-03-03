import psycopg2
from ..dbconfig import config
import time
import base64
from functions.log import logErrorToDB
from fastapi import HTTPException
import traceback


async def uploadMedia(file, username, sessionkey):
    # start timer
    task_start_time = time.time()

    try:
        conn = psycopg2.connect(config())

        with conn.cursor() as cur:
            cur.execute(
                "SELECT (sessioncookie) FROM users WHERE username = %s",
                (username,)
            )
            sessioncookie = cur.fetchone()

            if sessioncookie is None:
                time_task_took = time.time() - task_start_time
                return {
                    "detail": {
                        "APImessage": "failure",
                        "UIMessage": "That user does not exist.",
                        "username": username,
                        "attempt_time": int(str(time.time()).split(".")[0]),
                    },
                    "time_took": time_task_took,
                    "error_code": 0
                }

            else:  # user exists
                # are they allowed to upload files?
                cur.execute("SELECT (allowedtoupload) FROM users WHERE username=%s",
                            (username,))
                if not cur.fetchone()[0]:
                    time_task_took = time.time() - task_start_time
                    return {
                        "detail": {
                            "APImessage": "failure",
                            "error": "User not allowed to upload files.",
                            "UIMessage": "You're not allowed to upload files to Limits.",
                            "username": username,
                            "attempt_time": int(str(time.time()).split(".")[0]),
                        },
                        "time_took": time_task_took,
                        "error_code": 0
                    }

                if sessioncookie[0] == sessionkey:  # correct sesh key
                    time_task_took = time.time() - task_start_time

                    # base64 media
                    mediabase64 = base64.b64encode(await file.read()).decode("utf-8")

                    # get user id
                    cur.execute(
                        "SELECT (userid) FROM users WHERE username=%s",
                        (username,)
                    )
                    userid = cur.fetchone()

                    # find the highest media id
                    cur.execute("SELECT MAX(contentid) FROM media")
                    highest_id = cur.fetchone()[0] or 0

                    # upload media to cock db
                    cur.execute(
                        "INSERT INTO media (base64, userid, unixtimestamp, deleted, filename, contentid) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (mediabase64, userid, time.time(), "false", file.filename, (int(highest_id) + 1))
                    )
                    conn.commit()

                    return {
                        "detail": {
                            "APImessage": "success",
                            "UIMessage": "Media uploaded successfully.",
                            "contentid": str(int(highest_id) + 1),
                            "filename": file.filename,
                            "username": username,
                            "attempt_time": int(str(time.time()).split(".")[0]),
                        },
                        "time_took": time_task_took,
                        "error_code": 0
                    }

                else:  # session is wrong
                    time_task_took = time.time() - task_start_time
                    return {
                        "detail": {
                            "APImessage": "failure",
                            "error": "Invalid session key.",
                            "UIMessage": "Invalid session key.",
                            "username": username,
                            "attempt_time": int(str(time.time()).split(".")[0]),
                        },
                        "time_took": time_task_took,
                        "error_code": 0
                    }

    except (Exception, psycopg2.DatabaseError):
        time_task_took = time.time() - task_start_time
        await logErrorToDB(str(traceback.format_exc()), timetaken=time_task_took)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "1",
                "http_code": "500",
                "error": "Media upload error.",
                "time_took": time_task_took
            }
        )
