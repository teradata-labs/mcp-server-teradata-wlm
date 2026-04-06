"""
MCP Tool Functions for Teradata Workload Management Operations

This module contains all the tool functions that are exposed through the MCP server.
Each function implements a specific TDWM operation and returns properly formatted responses.
"""

import asyncio
import logging
from typing import Any, List

import mcp.types as types
from .tdwm_static import TDWM_CLASIFICATION_TYPE
from .oauth_context import require_oauth_authorization, get_oauth_error

# Import shared utilities from common module
from .fnc_common import (
    format_text_response,
    format_error_response,
    acquire_connection,
    _set_queryband,
    ResponseType,
    set_tools_connection,
    set_transport,
    with_connection_retry
)

# Import Priority 1 Configuration Management tools
from .fnc_tools_priority1 import (
    create_system_throttle,
    modify_throttle_limit,
    delete_throttle,
    enable_throttle,
    disable_throttle,
    create_filter,
    delete_filter,
    enable_filter,
    disable_filter,
    add_classification_to_rule,
    add_subcriteria_to_target,
    activate_ruleset,
    list_rulesets
)

logger = logging.getLogger(__name__)


# --- TDWM Tool Functions ---

@with_connection_retry()
async def list_sessions() -> ResponseType:
    """Show my sessions"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_sessions")
            cur = tdconn.cursor()
            rows = cur.execute("SELECT * FROM TABLE (monitormysessions()) as t1")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing sessions: {e}")
            return format_error_response("Failed to list sessions. Check server logs for details.")

@with_connection_retry()
async def monitor_amp_load() -> ResponseType:
    """Monitor AMP load"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "monitor_amp_load")
            cur = tdconn.cursor()
            rows = cur.execute("SELECT * FROM TABLE (MonitorAMPLoad()) AS t1")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error monitoring AMP load: {e}")
            return format_error_response("Failed to monitor AMP load. Check server logs for details.")

@with_connection_retry()
async def monitor_awt() -> ResponseType:
    """Monitor AWT (Amp Worker Tasks) resources"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "monitor_awt")
            cur = tdconn.cursor()
            rows = cur.execute("SELECT * FROM TABLE (MonitorAWTResource(1,2,3,4)) AS t1")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error monitoring AWT: {e}")
            return format_error_response("Failed to monitor AWT resources. Check server logs for details.")

@with_connection_retry()
async def monitor_config() -> ResponseType:
    """Monitor Teradata config"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "monitor_config")
            cur = tdconn.cursor()
            rows = cur.execute("SELECT t2.* FROM TABLE (MonitorVirtualConfig()) AS t2")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error monitoring config: {e}")
            return format_error_response("Failed to monitor config. Check server logs for details.")

@with_connection_retry()
async def list_resources() -> ResponseType:
    """Show physical resources"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_physical_resources")
            cur = tdconn.cursor()
            rows = cur.execute("SELECT t2.* from table (MonitorPhysicalResource()) as t2")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing physical resources: {e}")
            return format_error_response("Failed to list physical resources. Check server logs for details.")

@with_connection_retry()
async def identify_blocking() -> ResponseType:
    """Identify blocking users"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "identify_blocking")
            cur = tdconn.cursor()
            rows = cur.execute("""
                SELECT
                    IdentifyUser(blk1userid) as "blocking user",
                    IdentifyTable(blk1objtid) as "blocking table",
                    IdentifyDatabase(blk1objdbid) as "blocking db"
                FROM TABLE (MonitorSession(-1,'*',0)) AS t1
                WHERE Blk1UserId > 0""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error identifying blocking: {e}")
            return format_error_response("Failed to identify blocking sessions. Check server logs for details.")

@with_connection_retry()
async def abort_sessions_user(usr: str) -> ResponseType:
    """Abort sessions for a user {usr}"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "abort_sessions_user")
            cur = tdconn.cursor()
            rows = cur.execute("""
                SELECT AbortSessions (HostId, UserName, SessionNo, 'Y', 'Y')
                FROM TABLE (MonitorSession(-1, '*', 0)) AS t1
                WHERE username= ?""", [usr])
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error aborting sessions for user: {e}")
            return format_error_response("Failed to abort sessions. Check server logs for details.")

@with_connection_retry()
async def list_active_WD() -> ResponseType:
    """List active workloads (WD)"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "list_active_WD")
            cur = tdconn.cursor()
            rows = cur.execute("""sel * from table (tdwm.TDWMActiveWDs()) as t1""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error listing active workloads: {e}")
            return format_error_response("Failed to list active workloads. Check server logs for details.")

@with_connection_retry()
async def list_WDs() -> ResponseType:
    """List workloads (WD)"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "list_WD")
            cur = tdconn.cursor()
            rows = cur.execute("""SELECT * FROM TABLE (TDWM.TDWMListWDs('Y')) AS t1""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error listing workloads: {e}")
            return format_error_response("Failed to list workloads. Check server logs for details.")


@with_connection_retry()
async def show_session_sql_steps(SessionNo: int) -> ResponseType:
    """Show sql steps for a session {SessionNo}"""
    SessionNo = int(SessionNo)
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_sql_steps_for_session")
            cur = tdconn.cursor()
            rows = cur.execute("SELECT HostId, LogonPENo FROM TABLE (monitormysessions()) as t1 where SessionNo = ?", [SessionNo])
            row = rows.fetchall()[0]
            hostId = int(row[0])
            logonPENo = int(row[1])
            query = """
                select
                    SQLStep,
                    StepNum (format '99') Num,
                    Confidence (format '9') C,
                    EstRowCount (format '-99999999') ERC,
                    ActRowCount (format '99999999') ARC,
                    EstRowCountSkew (format '-99999999') ERCS,
                    ActRowCountSkew (format '99999999') ARCS,
                    EstRowCountSkewMatch (format '-99999999') ERCSM,
                    ActRowCountSkewMatch (format '99999999') ARCSM,
                    EstElapsedTime (format '99999') EET,
                    ActElapsedTime (format '99999') AET
                from
                    table (MonitorSQLSteps({hostId},{SessionNo},{logonPENo})) as t2
                """.format(hostId=hostId, SessionNo=SessionNo, logonPENo=logonPENo)
            cur1 = tdconn.cursor()
            rows1 = cur1.execute(query)
            return format_text_response(list(rows1.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing SQL steps: {e}")
            return format_error_response("Failed to show SQL steps. Check server logs for details.")

@with_connection_retry()
async def monitor_session_query_band(SessionNo: int) -> ResponseType:
    """Monitor query band for session {SessionNo}"""
    SessionNo = int(SessionNo)
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "monitor_session_query_band")
            cur = tdconn.cursor()
            rows = cur.execute("SELECT HostId, LogonPENo FROM TABLE (monitormysessions()) as t1 where SessionNo = ?", [SessionNo])
            row = rows.fetchall()[0]
            hostId = int(row[0])
            logonPENo = int(row[1])
            query = """
                SELECT MonitorQueryBand({hostId},{SessionNo},{logonPENo})
                """.format(hostId=hostId, SessionNo=SessionNo, logonPENo=logonPENo)
            cur1 = tdconn.cursor()
            rows1 = cur1.execute(query)
            return format_text_response(list(rows1.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error monitoring session query band: {e}")
            return format_error_response("Failed to monitor session query band. Check server logs for details.")

@with_connection_retry()
async def show_session_sql_text(SessionNo: int) -> ResponseType:
    """Show sql text for a session {SessionNo}"""
    SessionNo = int(SessionNo)
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_sql_text_for_session")
            cur = tdconn.cursor()
            rows = cur.execute("SELECT HostId, LogonPENo FROM TABLE (monitormysessions()) as t1 where SessionNo = ?", [SessionNo])
            row = rows.fetchall()[0]
            hostId = int(row[0])
            logonPENo = int(row[1])
            query = "SELECT SQLTxt FROM TABLE (MonitorSQLText({hostId},{SessionNo},{logonPENo})) as t2".format(hostId=hostId, SessionNo=SessionNo, logonPENo=logonPENo)
            cur1 = tdconn.cursor()
            rows1 = cur1.execute(query)
            return format_text_response(list(rows1.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing SQL text: {e}")
            return format_error_response("Failed to show SQL text. Check server logs for details.")

@with_connection_retry()
async def list_delayed_request() -> ResponseType:
    """List all of the delayed queries"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "list_delayed_request")
            cur = tdconn.cursor()
            rows = cur.execute("""
                SELECT * FROM TABLE (TDWM.TDWMGetDelayedQueries('O')) AS t1""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error listing delayed requests: {e}")
            return format_error_response("Failed to list delayed requests. Check server logs for details.")


@with_connection_retry()
async def abort_delayed_request(SessionNo: int) -> ResponseType:
    """Abort delay requests on session {SessionNo}"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "abort_delayed_request")
            cur = tdconn.cursor()
            rows = cur.execute("""
                SELECT TDWM.TDWMAbortDelayedRequest(HostId, SessionNo, RequestNo, 0)
                FROM TABLE (TDWM.TDWMGetDelayedQueries('O')) AS t1
                WHERE SessionNo=?""",[SessionNo])
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error aborting delayed request: {e}")
            return format_error_response("Failed to abort delayed request. Check server logs for details.")

@with_connection_retry()
async def list_utility_stats() -> ResponseType:
    """List statistics for use utilities"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "list_utility_stats")
            cur = tdconn.cursor()
            rows = cur.execute("""
                SELECT * FROM TABLE (TDWM.TDWMLoadUtilStatistics()) AS t1""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error listing utility stats: {e}")
            return format_error_response("Failed to list utility statistics. Check server logs for details.")

@with_connection_retry()
async def display_delay_queue(Type: str) -> ResponseType:
    """Display {Type} delay queue details"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "display_delay_queue")
            cur = tdconn.cursor()
            if Type.upper() == "WORKLOAD":
                rows = cur.execute("""
                    SELECT * FROM TABLE (TDWM.TDWMGetDelayedQueries('W')) AS t1;""")
            elif Type.upper() == "SYSTEM":
                rows = cur.execute("""
                    SELECT * FROM TABLE (TDWM.TDWMGetDelayedQueries('O')) AS t1""")
            elif Type.upper() == "UTILITY":
                rows = cur.execute("""
                    SELECT * FROM TABLE (TDWM.TDWMGetDelayedUtilities()) AS t1""")
            else:
                rows = cur.execute("""
                    SELECT * FROM TABLE (TDWM.TDWMGetDelayedQueries('A')) AS t1""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error displaying delay queue: {e}")
            return format_error_response("Failed to display delay queue. Check server logs for details.")

@with_connection_retry()
async def release_delay_queue(SessionNo: int, UserName: str) -> ResponseType:
    """Releases a request or utility session in the queue for session or user"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "release_delay_queue")
            cur = tdconn.cursor()
            if SessionNo:
                rows = cur.execute("""
                    SELECT TDWM.TDWMReleaseDelayedRequest(HostId, SessionNo, RequestNo, 0)
                    FROM TABLE (TDWMGetDelayedQueries('O')) AS t1
                    WHERE SessionNo=?""",[SessionNo])
            elif UserName:
                rows = cur.execute("""
                    SELECT TDWM.TDWMReleaseDelayedRequest(HostId, SessionNo, RequestNo, 0)
                    FROM TABLE (TDWMGetDelayedQueries('O')) AS t1
                    WHERE t1.Username=?""",[UserName])
            else:
                return format_error_response("Either sessionNo or userName must be provided.")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error releasing delay queue: {e}")
            return format_error_response("Failed to release delay queue. Check server logs for details.")

@with_connection_retry()
async def show_tdwm_summary() -> ResponseType:
    """Show workloads summary information"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_tdwm_summary")
            cur = tdconn.cursor()
            rows = cur.execute("""SELECT * FROM TABLE (TDWM.TDWMSummary()) AS t2""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing TDWM summary: {e}")
            return format_error_response("Failed to show TDWM summary. Check server logs for details.")

@with_connection_retry()
async def show_trottle_statistics(type: str) -> ResponseType:
    """Show throttle statistics for {type}"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_trottle_statistics")
            cur = tdconn.cursor()
            if type.upper() == "ALL":
                rows = cur.execute("""SELECT * FROM TABLE (TDWM.TDWMTHROTTLESTATISTICS('A')) AS t1""")
            elif type.upper() == "QUERY":
                rows = cur.execute("""SELECT * FROM TABLE (TDWM.TDWMTHROTTLESTATISTICS('Q')) AS t1""")
            elif type.upper() == "SESSION":
                rows = cur.execute("""SELECT * FROM TABLE (TDWM.TDWMTHROTTLESTATISTICS('S')) AS t1""")
            elif type.upper() == "WORKLOAD":
                rows = cur.execute("""SELECT * FROM TABLE (TDWM.TDWMTHROTTLESTATISTICS('W')) AS t1""")
            else:
                rows = cur.execute("""
                        SELECT ObjectType(FORMAT 'x(10)'), rulename(FORMAT 'x(17)'),
                            ObjectName(FORMAT 'x(13)'), active(FORMAT 'Z9'),
                            throttlelimit as ThrLimit, delayed(FORMAT 'Z9'), throttletype as ThrType
                        FROM TABLE (TDWM.TDWMTHROTTLESTATISTICS('A')) AS t1
                        ORDER BY 1,2""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing throttle statistics: {e}")
            return format_error_response("Failed to show throttle statistics. Check server logs for details.")

@with_connection_retry()
async def list_query_band(Type: str) -> ResponseType:
    """List query band for {Type}"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "list_query_band")
            cur = tdconn.cursor()
            if Type.upper() == "TRANSACTION":
                rows = cur.execute("""
                    SELECT * FROM TABLE(GetQueryBandPairs(1)) AS t1""")
            elif Type.upper() == "PROFILE":
                rows = cur.execute("""
                    SELECT * FROM TABLE(GetQueryBandPairs(3)) AS t1""")
            elif Type.upper() == "SESSION":
                rows = cur.execute("""
                    SELECT * FROM TABLE(GetQueryBandPairs(2)) AS t1""")
            else:
                rows = cur.execute("""
                    SELECT * FROM TABLE(GetQueryBandPairs(0)) AS t1""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error listing query band: {e}")
            return format_error_response("Failed to list query band. Check server logs for details.")

@with_connection_retry()
async def show_query_log(User: str) -> ResponseType:
    """Show query log for user {User}"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_query_log")
            cur = tdconn.cursor()
            rows = cur.execute("""
                    sel * from dbc.qrylogv where upper(username)=upper(?) and trunc(collectTimeStamp) = trunc(date) ORDER BY queryid""", [User])
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing query log: {e}")
            return format_error_response("Failed to show query log. Check server logs for details.")

@with_connection_retry()
async def show_cod_limits() -> ResponseType:
    """Show COD (Capacity On Demand) limits"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_cod_limits")
            cur = tdconn.cursor()
            rows = cur.execute("""
                    SELECT * FROM TABLE (TD_SYSFNLIB.TD_get_COD_Limits( ) ) As d""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing COD limits: {e}")
            return format_error_response("Failed to show COD limits. Check server logs for details.")

@with_connection_retry()
async def tdwm_list_clasification() -> ResponseType:
    """List classification types for workload (TASM) rule"""
    return format_text_response(list([(entry[1], entry[2], entry[3], entry[4]) for entry in TDWM_CLASIFICATION_TYPE]))

@with_connection_retry()
async def show_top_users(type: str) -> ResponseType:
    """Show {type} users using resources"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_top_users")
            cur = tdconn.cursor()
            if type.upper() == "TOP":
                query = """
                    Sel top 15 Username (Format 'x(10)'), queryband(Format 'x(40)'),AppID, ClientAddr, StartTime, AMPCPUTime, QueryText from dbc.qrylogV
                    where ampcputime > .154 order by ampcputime desc"""
            else:
                query = """
                    Sel Username (Format 'x(10)'), queryband(Format 'x(40)'),AppID, ClientAddr, StartTime, AMPCPUTime, QueryText from dbc.qrylogV
                    where ampcputime > .154 order by ampcputime desc"""
            rows = cur.execute(query)
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing top users: {e}")
            return format_error_response("Failed to show top users. Check server logs for details.")

@with_connection_retry()
async def show_sw_event_log(type: str) -> ResponseType:
    """Show {type} event log"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_sw_event_log")
            cur = tdconn.cursor()
            if type.upper() == "OPERATIONAL":
                query = """SELECT top 20
                    TheDate,
                    TheTime,
                    Event_Tag,
                    Category,
                    Severity,
                    Text,
                    PMA,
                    Vproc,
                    Partition,
                    Task,
                    TheFunction,
                    SW_Version,
                    Line
                FROM
                    DBC.SW_EVENT_LOG
                WHERE
                    (trunc(TheDate) between trunc(date-7) and trunc(date)) and
                    theFunction IS NOT NULL AND
                    Text LIKE '%operational%'
                ORDER BY
                    TheDate desc, TheTime desc;"""
            else:
                query = """SELECT top 20
                    TheDate,
                    TheTime,
                    Event_Tag,
                    Category,
                    Severity,
                    Text,
                    PMA,
                    Vproc,
                    Partition,
                    Task,
                    TheFunction,
                    SW_Version,
                    Line
                FROM
                    DBC.SW_EVENT_LOG
                WHERE
                    (trunc(TheDate) between trunc(date-1) and trunc(date)) and
                    theFunction IS NOT NULL AND
                    Text LIKE '%operational%' or Text LIKE '%Event%'
                ORDER BY
                    TheDate desc, TheTime desc;"""
            rows = cur.execute(query)
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing SW event log: {e}")
            return format_error_response("Failed to show event log. Check server logs for details.")

@with_connection_retry()
async def show_tasm_statistics() -> ResponseType:
    """Show TASM statistics"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_tasm_statistics")
            cur = tdconn.cursor()
            rows = cur.execute("""
                select
                    TheDatePN (FORMAT'yy/mm/dd', TITLE '// //Date'),
                    TheHour (TITLE '// //Hour'),
                    TheMinute (TITLE '// //Minute'),
                    DayOfWeek (TITLE 'Day of Week'),
                    NodeID (TITLE '//Node ID'),
                    rulenamePN (TITLE '//Workload//Name'),
                    ppidPN (FORMAT '9', TITLE '// //PP ID'),
                    pgidPN (FORMAT 'ZZ9', TITLE '// //PG ID')
                    ,average(CPUPctPN) (FORMAT 'ZZ9.9', TITLE 'CPU//Util// %')
                    ,average(PhysicalIOPN) (FORMAT 'ZZ9.9', TITLE 'Avg//I/Os//per Sec')
                    ,average(PhysicalIOMBPN) (FORMAT 'ZZ9.9', TITLE 'Avg//I/O Mbytes//per Sec')
                    ,average(WorkMsgSendDelayCntPN) (FORMAT 'ZZ9.9', TITLE '# AWT Requests//Successfully Sent//per AMP')
                    ,average(NumRequestsPN) (FORMAT 'ZZ9.9', TITLE '# Tasks//Assigned AWTs//per AMP')
                    ,average(AwtReleasesPN) (FORMAT 'ZZ9.9', TITLE '# AWTs//Released//per AMP')
                    ,average(QLengthAmpAvgAPN) (FORMAT 'ZZ9.9', TITLE '# Requests//Still Waiting//for AWT')
                    ,max(WorkMsgSendDelayMPN) (FORMAT 'ZZ9.99', TITLE 'Max//Send-Side//Wait')
                    ,max(QWaitTimeMaxMPN) (FORMAT 'ZZ9.99', TITLE 'Max//Receive-Side//Wait')
                    ,max(WorkMsgReceiveDelayMPN) (FORMAT 'ZZ9.99', TITLE 'Max//Receive-Side//Still Waiting')
                    ,average(zeroifnull(WorkMsgSendDelayRequestAPN)) (FORMAT 'ZZ9.99', TITLE 'Avg//Send-Side//Wait')
                    ,average(zeroifnull(QwaitTimeRequestAPN)) (FORMAT 'ZZ9.99', TITLE 'Avg//Receive- Side//Wait')
                    ,average(zeroifnull(WorkMsgReceiveDelayRequestAPN)) (FORMAT 'ZZ9.99', TITLE 'Avg//Receive-Side//Still Waiting')
                    ,max(ServiceTimeMPN) (FORMAT 'ZZ9.99', TITLE 'Max//Time//AWT Held')
                    ,average(zeroifnull(ServiceTimeAPN)) (FORMAT 'ZZ9.99', TITLE 'Avg//Time//AWT Held')
                    ,max(WorkTimeInUseMPN) (FORMAT 'ZZ9.99', TITLE 'Max//Time//AWT Held or Still Held')
                    ,average(AwtUsedAPN) (FORMAT 'ZZ9.9', TITLE 'Avg//AWTs//In Use')
                FROM
                (
                    select
                        t1.TheDate as TheDatePN
                        ,extract(hour from t1.thetime) TheHour
                        ,extract(Minute from t1.thetime) TheMinute
                        ,CASE WHEN day_of_week = 1 THEN 'Sunday'
                        WHEN day_of_week = 2 THEN 'Monday'
                        WHEN day_of_week = 3 THEN 'Tuesday'
                        WHEN day_of_week = 4 THEN 'Wednesday'
                        WHEN day_of_week = 5 THEN 'Thursday'
                        WHEN day_of_week = 6 THEN 'Friday'
                        WHEN day_of_week = 7 THEN 'Saturday'
                        END AS dayofweek,
                        NodeId,
                        rulename as
                        rulenamePN,
                        ppid as ppidPN,
                        pgid as pgidPN
                        ,SUM(CPUPct) as CPUPctPN
                        ,sum((PhysicalReadPerm +
                        PhysicalWritePerm+PhysicalReadOther+PhysicalWriteOther)/(CentiSecs/100)) as
                        PhysicalIOPN
                        ,sum((PhysicalReadPermKB +
                        PhysicalWritePermKB+PhysicalReadOtherKB+PhysicalWriteOtherKB)/(1024*CentiSecs/100)) as PhysicalIOMBPN
                        ,sum(WorkMsgSendDelayCnt/AmpCount) as WorkMsgSendDelayCntPN
                        ,sum(NumRequests/AmpCount) as NumRequestsPN
                        ,sum(AwtReleases/AmpCount) as AwtReleasesPN
                        ,sum(WorkMsgReceiveDelayCnt/AmpCount) as QLengthAmpAvgAPN
                        ,max(WorkMsgSendDelayMax) as WorkMsgSendDelayMPN
                        ,max(WorkMsgReceiveDelayMax) as WorkMsgReceiveDelayMPN
                        ,max(QWaitTimeMax) as QWaitTimeMaxMPN
                        ,sum(WorkMsgSendDelayRequestAvg) as WorkMsgSendDelayRequestAPN
                        ,sum(WorkMsgReceiveDelayRequestAvg) as WorkMsgReceiveDelayRequestAPN
                        ,sum(QWaitTimeRequestAvg) as QWaitTimeRequestAPN
                        ,sum(ServiceTimeRequestAvg) as ServiceTimeAPN
                        ,max(ServiceTimeMax) as ServiceTimeMPN
                        ,max(WorkTimeInUseMax) as WorkTimeInUseMPN
                        ,sum(AWTUsedAvg/AmpCount) as AwtUsedAPN
                    FROM
                        DBC.ResSpsView as T1
                        LEFT OUTER JOIN
                        tdwm.RuleDefs as T2
                        on (T1.WDid = T2.RuleId AND T2.RuleType =5)
                        inner join
                        sys_calendar.CALENDAR b
                        on calendar_date = thedate
                    where thedate = date and active >0 group by 1,2,3,4,5,6,7,8
                ) as SumPNTbl
                group by 1,2,3,4,5,6,7,8 order by 1,2,3,4,5,6,7""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing TASM statistics: {e}")
            return format_error_response("Failed to show TASM statistics. Check server logs for details.")

@with_connection_retry()
async def show_tasm_even_history() -> ResponseType:
    """Show TASM event history"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_tasm_even_history")
            cur = tdconn.cursor()
            rows = cur.execute("""
                SELECT entryts,
                    SUBSTR(entrykind,1,10) "kind",
                    SUBSTR (entryname,1,20) "name",
                    CAST (eventvalue as float format '999.9999') "evt value",
                    CAST (lastvalue as float format '999.9999') "last value",
                    spare2 "spare Int",
                    SUBSTR (activity,1,10) "activity id",
                    SUBSTR (activityname,1,20) "act name", seqno
                FROM tdwmeventhistory order by entryts, seqno""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing TASM event history: {e}")
            return format_error_response("Failed to show TASM event history. Check server logs for details.")

@with_connection_retry()
async def show_tasm_rule_history_red() -> ResponseType:
    """What caused the system to enter the RED state"""
    async with acquire_connection() as tdconn:
        def _run():
            _set_queryband(tdconn, "show_tasm_rule_history_red")
            cur = tdconn.cursor()
            rows = cur.execute("""
                WITH RECURSIVE
                CausalAnalysis(EntryTS,
                EntryKind, EntryID, EntryName, Activity,Activityid) AS
                (
                SELECT EntryTS, EntryKind, EntryID, EntryName, Activity, Activityid
                FROM DBC.TDWMEventHistory
                WHERE EntryKind = 'SYSCON' AND EntryName = 'RED' AND Activity = 'ACTIVE'
                UNION ALL
                SELECT Cause.EntryTS,Cause.EntryKind,Cause.EntryID,
                    Cause.EntryName,Cause.Activity,Cause.Activityid
                FROM CausalAnalysis Condition INNER JOIN DBC.TDWMEventHistory Cause
                ON Condition.EntryKind = Cause.Activity AND
                    Condition.EntryID = Cause.Activityid)
                SELECT * FROM CausalAnalysis
                ORDER BY 1 DESC""")
            return format_text_response(list(rows.fetchall()))
        try:
            return await asyncio.to_thread(_run)
        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error showing TASM rule history: {e}")
            return format_error_response("Failed to show TASM rule history. Check server logs for details.")

@with_connection_retry()
async def get_active_ruleset_name() -> str:
    """Get the currently active ruleset name."""
    try:
        async with acquire_connection() as tdconn:
            cur = tdconn.cursor()
            rows = cur.execute("""
                SELECT ConfigName
                FROM TDWM.Configurations
                WHERE ActiveFlag = 'Y'
                LIMIT 1
            """)
            result = rows.fetchone()
            return result[0] if result else "MyFirstConfig"
    except Exception as e:
        logger.warning(f"Error getting active ruleset, using default: {e}")
        return "MyFirstConfig"


# --- MCP Handler Functions ---

async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    logger.info("Listing tools")
    return [
        types.Tool(
            name="show_sessions",
            description="Display all active database sessions for the current user. Use this to monitor running queries, identify long-running operations, find session IDs for detailed analysis, or check current database activity. Returns session details including session number, username, SQL text, runtime, and state.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="show_physical_resources",
            description="Display current physical system resources including CPU, memory, and I/O utilization. Use this for capacity planning, health checks, or when investigating performance degradation. Returns metrics for CPU usage, memory consumption, disk I/O, and network activity across the system.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="monitor_amp_load",
            description="Monitor Access Module Processor (AMP) load and utilization. AMPs are Teradata's parallel processing units. Use this to check if the system is CPU-bound, identify AMP skew (unbalanced load distribution), or verify system capacity. Returns CPU utilization percentage for each AMP.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="monitor_awt",
            description="Monitor AMP Worker Task (AWT) resource usage. AWTs are the task slots that execute query operations. Use this to check if task slots are exhausted (causing query delays) or to understand concurrency limits. Returns current AWT usage, available slots, and task queue depth.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="monitor_config",
            description="Display virtual configuration settings for the Teradata system. Shows resource allocations, node configuration, and virtual system parameters. Use this to verify system setup, check VM resource allocations, or troubleshoot configuration issues. Returns virtual CPU, memory, and node configuration details.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="show_sql_steps_for_session",
            description="Display the execution plan steps for a specific session's query. Use this to analyze query performance, understand complex query execution, or troubleshoot slow queries. Requires sessionNo parameter. Returns detailed step-by-step execution plan with estimated costs and row counts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionNo": {
                        "type": "integer",
                        "description": "Session Number to retrieve execution steps for",
                    },
                },
                "required": ["sessionNo"],
            },
        ),
        types.Tool(
            name="show_sql_text_for_session",
            description="Display the full SQL text being executed by a specific session. Use this to see what query a session is running, especially useful when investigating blocking or performance issues. Requires sessionNo parameter. Returns the complete SQL statement text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionNo": {
                        "type": "integer",
                        "description": "Session Number to retrieve SQL text for",
                    },
                },
                "required": ["sessionNo"],
            },
        ),
        types.Tool(
            name="identify_blocking",
            description="Identify sessions that are blocking other sessions from executing. Use this when queries appear stuck or when investigating why queries are delayed. Returns information about blocking sessions (blockers) and blocked sessions (waiters), including session IDs and users involved.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="list_active_WD",
            description="List all currently active workload definitions (WD). Workloads are categories that classify and manage different types of queries (e.g., ETL, Reporting, Ad-hoc). Use this to see which workloads are enabled, verify workload configuration, or understand current workload management setup. Returns workload names, states, and basic configuration.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="list_WD",
            description="List ALL workload definitions, both active and inactive. Use this to see the complete workload inventory, identify inactive workloads that could be activated, or review the full workload management configuration. Returns all workload names with their active/inactive status.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="abort_sessions_user",
            description="TERMINATES all active sessions for a specified user. This immediately kills all running queries for that user. Use cautiously for emergency situations like runaway queries or when a user's sessions must be stopped. IMPORTANT: This cannot be undone and will rollback any uncommitted work. Requires user parameter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user": {
                        "type": "string",
                        "description": "Username whose sessions should be terminated (all sessions will be killed)",
                    },
                },
                "required": ["user"],
            },
        ),
        types.Tool(
            name="list_delayed_request",
            description="List all queries currently waiting in delay queues. Queries are delayed when they hit throttle limits, wait for locks, or are held by workload management rules. Use this to see why queries are waiting, identify queue backlogs, or check if specific users/queries are delayed. Returns session IDs, delay reasons, wait times, and queue types.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="abort_delayed_request",
            description="CANCEL and permanently abort a delayed query in the queue. The query will not execute and will be terminated. Use this to remove unnecessary or problematic queries from the queue. Requires sessionNo parameter. IMPORTANT: This cannot be undone - the query will need to be resubmitted if needed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionNo": {
                        "type": "integer",
                        "description": "Session Number of the delayed request to abort",
                    },
                },
                "required": ["sessionNo"],
            },
        ),
        types.Tool(
            name="list_utility_stats",
            description="Display statistics for utility operations (FastLoad, MultiLoad, TPump, etc.) running on the system. Use this to monitor utility performance, check if utilities are consuming excessive resources, or track utility usage patterns. Returns utility names, resource consumption, runtime, and status.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="display_delay_queue",
            description="Display details for a specific type of delay queue. Valid types: 'WORKLOAD' (throttled by workload rules), 'SYSTEM' (waiting for locks/resources), 'UTILITY' (utility operations queued), or 'ALL' (all queues). Use this to focus on a specific queue type when investigating delays. Returns detailed queue information including wait times, queue depth, and affected sessions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "type of delay queue",
                    },
                },
                "required": ["type"],
            },
        ),
        types.Tool(
            name="release_delay_queue",
            description="Release a delayed query from the queue, allowing it to execute immediately. Use this to manually override throttles or resolve stuck queries when system resources are available. Provide either sessionNo (for specific session) or userName (for all that user's delayed requests). CAUTION: Releasing many queries at once can overload the system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionNo": {
                        "type": "integer",
                        "description": "Session Number",
                    },
                    "userName": {
                        "type": "string",
                        "description": "User name to release",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="show_tdwm_summary",
            description="Display a summary dashboard of workload distribution across the system. Shows how queries and resources are distributed among different workloads. Use this to understand workload balance, verify classification is working correctly, or identify which workloads are consuming the most resources. Returns query counts, resource usage, and distribution metrics by workload.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="show_trottle_statistics",
            description="Display throttle statistics showing how throttles are managing query concurrency. Valid types: 'ALL' (all throttles), 'QUERY' (query-level throttles), 'SESSION' (session-level throttles), or 'WORKLOAD' (workload-level throttles). Use this to analyze throttle effectiveness, identify over-throttling, or verify throttle limits are working. Returns throttle names, limits, current usage, and delay counts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Type of throttle statistics",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="list_query_band",
            description="List query bands by type. Query bands are application-set tags that identify and classify queries. Valid types: 'TRANSACTION' (transaction-level bands), 'PROFILE' (profile-level bands), 'SESSION' (session-level bands), or 'ALL' (all types). Use this to understand how queries are being tagged, verify application query band usage, or troubleshoot workload classification. Returns query band names and values currently in use.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Type of query band",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="monitor_session_query_band",
            description="Display the query band settings for a specific session. Use this to see how a particular session is tagged, verify application is setting query bands correctly, or troubleshoot why a query is being classified into the wrong workload. Requires sessionNo parameter. Returns all query band name-value pairs for that session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionNo": {
                        "type": "integer",
                        "description": "Session Number",
                    },
                },
                "required": ["sessionNo"],
            },
        ),
        types.Tool(
            name="show_query_log",
            description="Display historical query log (DBQL) for a specific user. Shows past query execution including SQL text, execution times, resource consumption, and performance metrics. Use this to analyze user query patterns, identify frequently-slow queries, or investigate historical performance issues. Requires user parameter. Returns query history with timestamps, SQL, runtime, CPU time, and I/O statistics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user": {
                        "type": "string",
                        "description": "User name",
                    },
                },
                "required": ["user"],
            },
        ),
        types.Tool(
            name="show_cod_limits",
            description="Display Capacity on Demand (COD) resource limits and usage. COD allows temporary capacity increases beyond base system. Use this for capacity planning, checking if temporary capacity is available, or monitoring COD resource consumption. Returns COD limits, current usage, and available temporary capacity.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="tdwm_list_clasification",
            description="List all available classification types that can be used in TASM (Teradata Active System Management) workload rules. Classification types include USER, APPL, TABLE, QUERYBAND, etc. Use this to see what criteria are available when creating or modifying workload rules, throttles, or filters. Returns classification types with their categories and expected value formats.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="show_top_users",
            description="Display users consuming the most system resources. Valid types: 'TOP' (top consumers), 'ALL' (all users), or 'SYSTEM' (system accounts). Use this to identify resource-heavy users, find sources of system load, or track resource consumption by user for chargeback. Returns usernames, CPU time, I/O, spool usage, and query counts ranked by resource consumption.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "top users",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="show_sw_event_log",
            description="Display system software event logs. Valid types: 'OPERATIONAL' (operational events) or 'ALL' (all event types). Use this to troubleshoot system issues, review recent system events, or investigate errors and warnings. Returns timestamped event log entries with event types, severity, and descriptions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "Type": {
                        "type": "string",
                        "description": "Type of the events",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="show_tasm_statistics",
            description="Display Teradata Active System Management (TASM) performance statistics. Shows how workload management rules are functioning, including rule activations, exceptions, throttle actions, and workload classifications. Use this to verify TASM is working correctly, identify rule effectiveness, or troubleshoot workload management issues. Returns TASM metrics including rule firing counts, exception counts, and classification statistics.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="show_tasm_even_history",
            description="Display historical TASM event log showing when workload management rules fired and what actions were taken. Use this to understand TASM behavior over time, troubleshoot why queries were delayed/rejected, or analyze workload management patterns. Returns timestamped TASM events including rule names, actions taken, and affected queries.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="show_tasm_rule_history_red",
            description="Display the events and conditions that caused the system to enter RED state (critical resource shortage). RED state indicates severe resource constraints triggering emergency workload management actions. Use this to diagnose system overload incidents, understand what caused critical resource exhaustion, or perform post-incident analysis. Returns events leading to RED state including resource thresholds exceeded and timeline.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # ========== Priority 1 Configuration Management Tools ==========
        types.Tool(
            name="create_system_throttle",
            description="Create a new system-level throttle rule to limit concurrent query execution. Throttles prevent resource monopolization by restricting how many queries can run simultaneously. Use this to control system load, prevent specific query types from overwhelming resources, or enforce concurrency limits during business hours. REQUIRES: ruleset_name, throttle_name, description, limit (concurrent queries allowed). OPTIONAL: classification_criteria (to target specific apps/users/tables), throttle_type (DM=member with disable override). IMPORTANT: Changes require activation - call activate_ruleset after creation to make the throttle live.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {
                        "type": "string",
                        "description": "Ruleset name (e.g., 'MyFirstConfig')"
                    },
                    "throttle_name": {
                        "type": "string",
                        "description": "Name for the new throttle"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of throttle purpose"
                    },
                    "throttle_type": {
                        "type": "string",
                        "description": "Type: DM=disable override member, M=member",
                        "default": "DM"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum concurrent queries allowed",
                        "minimum": 1
                    },
                    "classification_criteria": {
                        "type": "array",
                        "description": "Optional list of classification criteria",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "type": {"type": "string"},
                                "value": {"type": "string"},
                                "operator": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["ruleset_name", "throttle_name", "description", "limit"]
            },
        ),
        types.Tool(
            name="modify_throttle_limit",
            description="Dynamically adjust the concurrency limit of an existing throttle without recreating it. Use this to increase/decrease throttle limits based on time of day, system load, or changing business needs. REQUIRES: ruleset_name, throttle_name, new_limit. CHANGES REQUIRE ACTIVATION: Call activate_ruleset after modification.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {
                        "type": "string",
                        "description": "Ruleset name containing the throttle"
                    },
                    "throttle_name": {
                        "type": "string",
                        "description": "Name of the throttle to modify"
                    },
                    "new_limit": {
                        "type": "integer",
                        "description": "New concurrency limit",
                        "minimum": 1
                    }
                },
                "required": ["ruleset_name", "throttle_name", "new_limit"]
            },
        ),
        types.Tool(
            name="delete_throttle",
            description="PERMANENTLY DELETE a throttle rule from the ruleset configuration. REQUIRES: ruleset_name, throttle_name. CHANGES REQUIRE ACTIVATION. CAUTION: Deletion is permanent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Ruleset name containing the throttle"},
                    "throttle_name": {"type": "string", "description": "Name of the throttle to delete"}
                },
                "required": ["ruleset_name", "throttle_name"]
            },
        ),
        types.Tool(
            name="enable_throttle",
            description="Enable (activate) a previously disabled throttle rule. REQUIRES: ruleset_name, throttle_name. CHANGES REQUIRE ACTIVATION.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Ruleset name containing the throttle"},
                    "throttle_name": {"type": "string", "description": "Name of the throttle to enable"}
                },
                "required": ["ruleset_name", "throttle_name"]
            },
        ),
        types.Tool(
            name="disable_throttle",
            description="Disable (deactivate) a throttle rule without deleting it. REQUIRES: ruleset_name, throttle_name. CHANGES REQUIRE ACTIVATION.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Ruleset name containing the throttle"},
                    "throttle_name": {"type": "string", "description": "Name of the throttle to disable"}
                },
                "required": ["ruleset_name", "throttle_name"]
            },
        ),
        types.Tool(
            name="create_filter",
            description="Create a filter rule to BLOCK or REJECT queries matching specific criteria. REQUIRES: ruleset_name, filter_name, description. OPTIONAL: classification_criteria, action ('E'=Exception/reject, 'A'=Abort). CHANGES REQUIRE ACTIVATION. CAUTION: Filters PREVENT query execution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Ruleset name"},
                    "filter_name": {"type": "string", "description": "Name for the new filter"},
                    "description": {"type": "string", "description": "Description of filter purpose"},
                    "classification_criteria": {
                        "type": "array",
                        "description": "List of classification criteria to match",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "type": {"type": "string"},
                                "value": {"type": "string"},
                                "operator": {"type": "string"}
                            }
                        }
                    },
                    "action": {"type": "string", "description": "Action: E=Exception (reject), A=Abort", "default": "E"}
                },
                "required": ["ruleset_name", "filter_name", "description"]
            },
        ),
        types.Tool(
            name="delete_filter",
            description="PERMANENTLY DELETE a filter rule. REQUIRES: ruleset_name, filter_name. CHANGES REQUIRE ACTIVATION.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Ruleset name containing the filter"},
                    "filter_name": {"type": "string", "description": "Name of the filter to delete"}
                },
                "required": ["ruleset_name", "filter_name"]
            },
        ),
        types.Tool(
            name="enable_filter",
            description="Enable (activate) a previously disabled filter rule. REQUIRES: ruleset_name, filter_name. CHANGES REQUIRE ACTIVATION.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Ruleset name containing the filter"},
                    "filter_name": {"type": "string", "description": "Name of the filter to enable"}
                },
                "required": ["ruleset_name", "filter_name"]
            },
        ),
        types.Tool(
            name="disable_filter",
            description="Disable (deactivate) a filter rule without deleting it. REQUIRES: ruleset_name, filter_name. CHANGES REQUIRE ACTIVATION.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Ruleset name containing the filter"},
                    "filter_name": {"type": "string", "description": "Name of the filter to disable"}
                },
                "required": ["ruleset_name", "filter_name"]
            },
        ),
        types.Tool(
            name="add_classification_to_rule",
            description="Add classification criteria to an existing rule (throttle, filter, or workload). Classification types: USER, APPL, TABLE, QUERYBAND, STMT, CLIENTADDR, etc. REQUIRES: ruleset_name, rule_name, description, classification_type, classification_value. OPTIONAL: operator ('I'=Inclusion, 'O'=ORing, 'IO'=Both). CHANGES REQUIRE ACTIVATION.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Ruleset name"},
                    "rule_name": {"type": "string", "description": "Name of the rule to modify"},
                    "description": {"type": "string", "description": "Description of this classification"},
                    "classification_type": {"type": "string", "description": "Type (USER, APPL, TABLE, QUERYBAND, etc.)"},
                    "classification_value": {"type": "string", "description": "Value to match"},
                    "operator": {"type": "string", "description": "Operator: I=Inclusion, O=ORing, IO=Both", "default": "I"}
                },
                "required": ["ruleset_name", "rule_name", "description", "classification_type", "classification_value"]
            },
        ),
        types.Tool(
            name="add_subcriteria_to_target",
            description="Add sub-criteria to a target classification for advanced rule targeting. Sub-criteria types: FTSCAN, MINSTEPTIME, MAXSTEPTIME, JOIN, MEMORY. REQUIRES: ruleset_name, rule_name, target_type, target_value, description, subcriteria_type. CHANGES REQUIRE ACTIVATION.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Ruleset name"},
                    "rule_name": {"type": "string", "description": "Name of the rule"},
                    "target_type": {"type": "string", "description": "Type of target (TABLE, DB, VIEW, etc.)"},
                    "target_value": {"type": "string", "description": "Value of target (e.g., 'myDB.TableA')"},
                    "description": {"type": "string", "description": "Description of sub-criteria"},
                    "subcriteria_type": {"type": "string", "description": "Sub-criteria type (FTSCAN, MINSTEPTIME, JOIN, etc.)"},
                    "subcriteria_value": {"type": "string", "description": "Value for sub-criteria"},
                    "operator": {"type": "string", "description": "Operator: I=Inclusion", "default": "I"}
                },
                "required": ["ruleset_name", "rule_name", "target_type", "target_value", "description", "subcriteria_type"]
            },
        ),
        types.Tool(
            name="activate_ruleset",
            description="ACTIVATE a ruleset to apply ALL pending configuration changes to the live system. MUST BE CALLED after any create, modify, enable, disable, or delete operations. REQUIRES: ruleset_name. IMMEDIATE EFFECT.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ruleset_name": {"type": "string", "description": "Name of the ruleset to activate"}
                },
                "required": ["ruleset_name"]
            },
        ),
        types.Tool(
            name="list_rulesets",
            description="List all available rulesets (configuration containers) in the system. Returns ruleset names with their active/inactive status.",
            inputSchema={
                "type": "object",
                "properties": {}
            },
        ),
    ]


async def handle_tool_call(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests with OAuth authorization.
    Tools can modify server state and notify clients of changes.
    """
    logger.info(f"Calling tool: {name}::{arguments}")

    # Check OAuth authorization for this tool
    if not require_oauth_authorization(name):
        error_msg = get_oauth_error(name)
        logger.warning(f"OAuth authorization failed for tool {name}: {error_msg}")
        return [types.TextContent(type="text", text=f"Authorization Error: {error_msg}")]

    try:
        if name == "show_sessions":
            return await list_sessions()
        elif name == "show_physical_resources":
            return await list_resources()
        elif name == "monitor_amp_load":
            return await monitor_amp_load()
        elif name == "monitor_awt":
            return await monitor_awt()
        elif name == "monitor_config":
            return await monitor_config()
        elif name == "show_sql_steps_for_session":
            return await show_session_sql_steps(arguments["sessionNo"])
        elif name == "show_sql_text_for_session":
            return await show_session_sql_text(arguments["sessionNo"])
        elif name == "identify_blocking":
            return await identify_blocking()
        elif name == "abort_sessions_user":
            return await abort_sessions_user(arguments["user"])
        elif name == "list_active_WD":
            return await list_active_WD()
        elif name == "list_WD":
            return await list_WDs()
        elif name == "list_delayed_request":
            return await list_delayed_request()
        elif name == "abort_delayed_request":
            return await abort_delayed_request(arguments["sessionNo"])
        elif name == "list_utility_stats":
            return await list_utility_stats()
        elif name == "display_delay_queue":
            return await display_delay_queue(arguments["type"])
        elif name == "release_delay_queue":
            return await release_delay_queue(
                arguments.get("sessionNo"),
                arguments.get("userName")
            )
        elif name == "show_tdwm_summary":
            return await show_tdwm_summary()
        elif name == "show_trottle_statistics":
            return await show_trottle_statistics(arguments.get("type", "ALL"))
        elif name == "list_query_band":
            return await list_query_band(arguments.get("type", "ALL"))
        elif name == "monitor_session_query_band":
            return await monitor_session_query_band(arguments["sessionNo"])
        elif name == "show_query_log":
            return await show_query_log(arguments["user"])
        elif name == "show_cod_limits":
            return await show_cod_limits()
        elif name == "tdwm_list_clasification":
            return await tdwm_list_clasification()
        elif name == "show_top_users":
            return await show_top_users(arguments.get("type", "ALL"))
        elif name == "show_sw_event_log":
            return await show_sw_event_log(arguments.get("Type", "ALL"))
        elif name == "show_tasm_statistics":
            return await show_tasm_statistics()
        elif name == "show_tasm_even_history":
            return await show_tasm_even_history()
        elif name == "show_tasm_rule_history_red":
            return await show_tasm_rule_history_red()
        # ========== Priority 1 Configuration Management Dispatch ==========
        elif name == "create_system_throttle":
            return await create_system_throttle(
                arguments["ruleset_name"],
                arguments["throttle_name"],
                arguments["description"],
                arguments.get("throttle_type", "DM"),
                arguments["limit"],
                arguments.get("classification_criteria")
            )
        elif name == "modify_throttle_limit":
            return await modify_throttle_limit(
                arguments["ruleset_name"],
                arguments["throttle_name"],
                arguments["new_limit"]
            )
        elif name == "delete_throttle":
            return await delete_throttle(
                arguments["ruleset_name"],
                arguments["throttle_name"]
            )
        elif name == "enable_throttle":
            return await enable_throttle(
                arguments["ruleset_name"],
                arguments["throttle_name"]
            )
        elif name == "disable_throttle":
            return await disable_throttle(
                arguments["ruleset_name"],
                arguments["throttle_name"]
            )
        elif name == "create_filter":
            return await create_filter(
                arguments["ruleset_name"],
                arguments["filter_name"],
                arguments["description"],
                arguments.get("classification_criteria"),
                arguments.get("action", "E")
            )
        elif name == "delete_filter":
            return await delete_filter(
                arguments["ruleset_name"],
                arguments["filter_name"]
            )
        elif name == "enable_filter":
            return await enable_filter(
                arguments["ruleset_name"],
                arguments["filter_name"]
            )
        elif name == "disable_filter":
            return await disable_filter(
                arguments["ruleset_name"],
                arguments["filter_name"]
            )
        elif name == "add_classification_to_rule":
            return await add_classification_to_rule(
                arguments["ruleset_name"],
                arguments["rule_name"],
                arguments["description"],
                arguments["classification_type"],
                arguments["classification_value"],
                arguments.get("operator", "I")
            )
        elif name == "add_subcriteria_to_target":
            return await add_subcriteria_to_target(
                arguments["ruleset_name"],
                arguments["rule_name"],
                arguments["target_type"],
                arguments["target_value"],
                arguments["description"],
                arguments["subcriteria_type"],
                arguments.get("subcriteria_value"),
                arguments.get("operator", "I")
            )
        elif name == "activate_ruleset":
            return await activate_ruleset(
                arguments["ruleset_name"]
            )
        elif name == "list_rulesets":
            return await list_rulesets()
        return [types.TextContent(type="text", text=f"Unsupported tool: {name}")]

    except ConnectionError as e:
        logger.error(f"Connection error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text="Database connection error. Please check your database connection and try again."
        )]
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error executing tool {name}. An internal error occurred. Check server logs for details."
        )]
