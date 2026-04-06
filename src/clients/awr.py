import psycopg2
import oracledb
from datetime import timedelta, datetime
from abc import ABC, abstractmethod
from confluence.tag import attachment, tag


class AWRReports(ABC):
    def __init__(self, host, port, login, password, start_date: datetime, load_plan: list, snap_delta=15) -> None:
        self.start_date = start_date
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.load_plan = load_plan
        self.snap_delta = snap_delta
        self.offset_left = 0
        self.offset_right = 0
        self.awr_reports = None

    def render(self):
        pass

    def shift_time_load(self):
        shift_time = 0
        for step in self.load_plan:
            up_time = step[0]
            hold_time = step[1]
            down_time = step[2]
            load_level = step[3]
            shift_time = up_time + shift_time
            duration_time = hold_time - self.offset_left - self.offset_right
            yield load_level, shift_time + self.offset_left, duration_time
            shift_time += hold_time + down_time

    def filter_snap(self, snaps, start_date, end_date):
        for snap_id, date in snaps.items():
            if start_date < date and date + timedelta(minutes=self.snap_delta) < end_date:
                return snap_id, date

    def upload_attachment(self, confluence, page_id):
        for load_level, awr_report in self.awr_reports.items():
            confluence.attach_content(awr_report, name=f'awr_report_level_{load_level}.html', content_type='text/html', page_id=page_id)

    def to_xml(self):
        result = []
        for load_level in self.awr_reports:
            result.append(attachment(f'awr_report_level_{load_level}.html'))
            result.append(tag('br'))
        return result

    @abstractmethod
    def get_awr(self):
        pass


class AWROracle(AWRReports):
    def __init__(self, host, port, sid, login, password, start_date: datetime, load_plan: list,
                 snap_delta=15) -> None:
        super().__init__(host, port, login, password, start_date, load_plan, snap_delta)
        self.string_connect = f'oracle://{login}:{password}@{host}:{port}/{sid}'
        # self.dsn = oracledb.makedsn(host, port, service_name=sid)
        cp = oracledb.ConnectParams(host=host, port=port, service_name=sid)
        self.dsn = cp.get_connect_string()
        self.query_db_id = 'select dbid from v$database where rownum <= 1'
        self.query_snap_id = 'select snap_id, begin_interval_time from dba_hist_snapshot where dbid = {0} order by begin_interval_time desc'
        self.query_awr = 'select output from table(sys.dbms_workload_repository.awr_report_html({0},  1, {1:d}, {2:d}))'

    def get_db_id(self, connection):
        with connection.cursor() as cursor:
            return cursor.execute(self.query_db_id).fetchone()[0]

    def get_snap_ids(self, connection, dbid):
        with connection.cursor() as cursor:
            result_proxy = cursor.execute(self.query_snap_id.format(dbid)).fetchall()
            return {row[0]: row[1] for row in result_proxy}

    def get_awr(self):
        # engine = create_engine(self.string_connect, echo=False)
        # start_date = datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S')
        self.awr_reports = {}
        with oracledb.connect(user=self.login, password=self.password, dsn=self.dsn,
                               encoding="UTF-8") as connection:
            db_id = self.get_db_id(connection)
            snap_ids = self.get_snap_ids(connection, db_id)
            for load_level, shift_time, duration_time in self.shift_time_load():
                snap = self.filter_snap(snap_ids,
                                        self.start_date + timedelta(minutes=shift_time),
                                        self.start_date + timedelta(minutes=shift_time + duration_time))
                snap_id = snap[0]
                with connection.cursor() as cursor:
                    result_proxy = cursor.execute(self.query_awr.format(db_id, snap_id, snap_id + 1))
                    self.awr_reports[load_level] = ''.join([row[0] for row in result_proxy if row[0] is not None])


class AWRPostgres(AWRReports):
    def __init__(self, host, port, dbname, login, password, start_date: datetime, load_plan: list,
                 snap_delta=15) -> None:
        super().__init__(host, port, login, password, start_date, load_plan, snap_delta)
        self.dbname = dbname
        self.connection_string = f"host='{host}' port='{port}' dbname='{dbname}' user='{login}' password='{password}'"
        self.query_snap_list = 'select * from __rds_pg_stats__.snap_list ORDER BY id'
        self.query_awr = 'select * from __rds_pg_stats__.snap_report_global({0}, {1})'

    def get_snap_list(self, connection):
        with connection.cursor() as cursor:
            cursor.execute(self.query_snap_list)
            result_proxy = cursor.fetchall()
            return {row[0]: row[1] for row in result_proxy}

    def get_awr(self):
        self.awr_reports = {}
        with psycopg2.connect(self.connection_string) as connection:
            snap_ids = self.get_snap_list(connection)
            for load_level, shift_time, duration_time in self.shift_time_load():
                snap = self.filter_snap(snap_ids,
                                        self.start_date + timedelta(minutes=shift_time),
                                        self.start_date + timedelta(minutes=shift_time + duration_time))
                snap_id = snap[0]
                with connection.cursor() as cursor:
                    cursor.execute(self.query_awr.format(snap_id, snap_id + 1))
                    result_proxy = cursor.fetchall()
                    if result_proxy:
                        self.awr_reports[load_level] = ''.join([row[0] for row in result_proxy if row[0] is not None])
