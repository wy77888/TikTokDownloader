from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Callable
from typing import Coroutine
from typing import TYPE_CHECKING
from typing import Type
from typing import Union

from ..interface.template import API
from ..testers import Params

if TYPE_CHECKING:
    from ..config import Parameter


class Account(API):
    post_api = f"{API.domain}aweme/v1/web/aweme/post/"
    favorite_api = f"{API.domain}aweme/v1/web/aweme/favorite/"

    def __init__(self,
                 params: Union["Parameter", Params],
                 cookie: str | dict = None,
                 proxy: str = None,
                 sec_user_id: str = ...,
                 tab="post",
                 earliest: str | float | int = "",
                 latest="",
                 pages: int = None,
                 cursor=0,
                 count=18,
                 *args,
                 **kwargs,
                 ):
        super().__init__(params, cookie, proxy, *args, **kwargs, )
        self.sec_user_id = sec_user_id
        self.api, self.favorite, self.pages = self.check_type(
            tab, pages or params.max_pages)
        self.latest: date = self.check_latest(latest)
        self.earliest: date = self.check_earliest(earliest)
        self.cursor = cursor
        self.count = count
        self.text = "账号喜欢作品" if self.favorite else "账号发布作品"

    async def run(self,
                  referer: str = None,
                  single_page=False,
                  data_key: str = "aweme_list",
                  error_text="该账号为私密账号，需要使用登录后的 Cookie，且登录的账号需要关注该私密账号",
                  cursor="max_cursor",
                  has_more="has_more",
                  params: Callable = lambda: {},
                  data: Callable = lambda: {},
                  method="GET",
                  headers: dict = None,
                  *args,
                  **kwargs, ):
        if self.favorite:
            self.set_referer(
                f"{self.domain}user/{self.sec_user_id}?showTab=like")
        else:
            self.set_referer(f"{self.domain}user/{self.sec_user_id}")
        match single_page:
            case True:
                await self.run_single(
                    data_key,
                    error_text,
                    cursor,
                    has_more,
                    params,
                    data,
                    method,
                    headers,
                    *args,
                    **kwargs,
                )
                return self.response
            case False:
                await self.run_batch(
                    data_key,
                    error_text,
                    cursor,
                    has_more,
                    params,
                    data,
                    method,
                    headers,
                    *args,
                    **kwargs,
                )
                return self.response, self.earliest, self.latest
        raise ValueError

    async def run_single(self,
                         data_key: str = "aweme_list",
                         error_text="该账号为私密账号，需要使用登录后的 Cookie，且登录的账号需要关注该私密账号",
                         cursor="max_cursor",
                         has_more="has_more",
                         params: Callable = lambda: {},
                         data: Callable = lambda: {},
                         method="GET",
                         headers: dict = None,
                         *args,
                         **kwargs,
                         ):
        await super().run_single(
            data_key,
            error_text,
            cursor,
            has_more,
            params,
            data,
            method,
            headers,
            *args,
            **kwargs,
        )

    async def run_batch(self,
                        data_key: str = "aweme_list",
                        error_text="该账号为私密账号，需要使用登录后的 Cookie，且登录的账号需要关注该私密账号",
                        cursor="max_cursor",
                        has_more="has_more",
                        params: Callable = lambda: {},
                        data: Callable = lambda: {},
                        method="GET",
                        headers: dict = None,
                        callback: Type[Coroutine] = None,
                        *args,
                        **kwargs,
                        ):
        await super().run_batch(
            data_key,
            error_text,
            cursor,
            has_more,
            params,
            data,
            method,
            headers,
            callback=callback or self.early_stop,
            *args,
            **kwargs,
        )
        self.summary_works()
        # await self.favorite_mode()

    # async def favorite_mode(self):
    #     if not self.favorite:
    #         return
    #     info = Extractor.get_user_info(await self.info.run())
    #     if self.sec_user_id != (s := info.get("sec_uid")):
    #         self.log.error(
    #             f"sec_user_id {self.sec_user_id} 与 {s} 不一致")
    #         self._generate_temp_data()
    #     else:
    #         self.response.append({"author": info})

    # def _generate_temp_data(self, ):
    #     temp_data = timestamp()
    #     self.log.warning(f"获取账号昵称失败，本次运行将临时使用 {temp_data} 作为账号昵称和 UID")
    #     temp_dict = {
    #         "author": {
    #             "nickname": temp_data,
    #             "uid": temp_data,
    #             "sec_uid": self.sec_user_id,
    #         }
    #     }
    #     self.response.append(temp_dict)

    async def early_stop(self):
        """如果获取数据的发布日期已经早于限制日期，就不需要再获取下一页的数据了"""
        if not self.favorite and self.earliest > datetime.fromtimestamp(
                max(int(self.cursor) / 1000, 0)).date():
            self.finished = True

    def generate_params(self, ) -> dict:
        match self.favorite:
            case True:
                return self.generate_favorite_params()
            case False:
                return self.generate_post_params()

    def generate_favorite_params(self) -> dict:
        return self.params | {
            "sec_user_id": self.sec_user_id,
            "max_cursor": self.cursor,
            "min_cursor": "0",
            "whale_cut_token": "",
            "cut_version": "1",
            "count": self.count,
            "publish_video_strategy_type": "2",
            "version_code": "170400",
            "version_name": "17.4.0",
        }

    def generate_post_params(self) -> dict:
        return self.params | {
            "sec_user_id": self.sec_user_id,
            "max_cursor": self.cursor,
            "locate_query": "false",
            "show_live_replay_strategy": "1",
            "need_time_list": "1",
            "time_list_query": "0",
            "whale_cut_token": "",
            "cut_version": "1",
            "count": self.count,
            "publish_video_strategy_type": "2",
        }

    def check_type(self, tab: str, pages: int) -> tuple[str, bool, int]:
        match tab:
            case "favorite":
                return self.favorite_api, True, pages
            case "post":
                pass
            case _:
                self.log.warning(f"tab 参数 {tab} 设置错误，程序将使用默认值: post")
        return self.post_api, False, 99999

    def check_earliest(self, date_: str | float | int) -> date:
        default_date = date(2016, 9, 20)  # 默认日期
        if not date_:  # 如果没有提供日期，返回默认日期
            return default_date
        if isinstance(date_, (int, float)):
            earliest = self.latest - timedelta(days=date_)  # 计算最早日期
            assert isinstance(earliest, date)
        elif isinstance(date_, str):
            try:
                earliest = datetime.strptime(date_, "%Y/%m/%d").date()  # 解析日期
            except ValueError:
                self.log.warning(f"作品最早发布日期 {date_} 无效")
                return default_date  # 无效日期返回默认日期
        else:
            raise ValueError(f"作品最早发布日期参数 {date_} 类型错误")
        self.log.info(f"作品最早发布日期: {earliest}")
        return earliest  # 返回 date 对象

    def check_latest(self, date_: str) -> date:
        default_date = date.today()  # 默认日期
        if not date_:
            return default_date
        try:
            latest = datetime.strptime(date_, "%Y/%m/%d").date()
            self.log.info(f"作品最晚发布日期: {latest}")
            return latest
        except ValueError:
            self.log.warning(f"作品最晚发布日期无效 {date_}")
            return default_date
