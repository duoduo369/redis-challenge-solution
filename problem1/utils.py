# -*- coding: utf-8 -*-
import redis

def get_connection():
    # TODO: use connection pool
    return redis.StrictRedis()

def calculate_score(votes, item_hour_age, gravity=1.5):
    '''最热帖子，最热视频列表。

    http://www.cnblogs.com/zhengyun_ustc/archive/2010/12/15/amir.html

    (p – 1) / (t + 2)^1.5

    其中，
    1）p 表示文章得到的投票数，之所以要使用 (p – 1)，应该是想
    去掉文章提交者的那一票。
    2）(t + 2)^1.5， 这个是时间因子。t 表示当前时间与文章提交
    时间间隔的小时数。但为什么要加 2 之后再取 1.5 的幂，似乎就
    没什么道理可言了，也许是个 trial-and-error 的结果吧。
    '''
    return (votes - 1) / pow((item_hour_age+2), gravity)
