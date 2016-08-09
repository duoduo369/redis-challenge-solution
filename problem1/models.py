# -*- coding: utf-8 -*-
from __future__ import absolute_import

import time
from datetime import datetime
from faker import Faker
from utils import get_connection, calculate_score

faker_factory = Faker()

class Model(object):
    table_name = ''

    @classmethod
    def create(cls, conn=None, *args, **kwargs):
        pass

    @classmethod
    def get_connection(cls, conn=None):
        if not conn:
            conn = get_connection()
        return conn

    @classmethod
    def generate_data(cls, n=1, conn=None, *args, **kwargs):
        pass


class VideoScore(Model):
    '''
    按照得分排序用的
    tables:
        video_score:
    type: zset
    detail:
        video:1 483
        video:2 345
    '''
    table_name = 'video_score:'

    @classmethod
    def create(cls, video_key, score, conn=None, *args, **kwargs):
        conn = cls.get_connection()
        conn.zadd(cls.table_name, score, video_key)

    @classmethod
    def add(cls, video_key, score, conn=None, *args, **kwargs):
        conn = cls.get_connection()
        conn.zincrby(cls.table_name, video_key, score)

    @classmethod
    def reduce(cls, video_key, score, conn=None, *args, **kwargs):
        conn = cls.get_connection()
        score = 0 - score
        conn.zincrby(cls.table_name, video_key, score)


class VideoCreateTime(Model):
    '''
    按照时间排序用的
    type: zset
    tables:
        video_createtime:
    detail:
        video:1 132345723.01
        video:2 132345745.33
    '''
    table_name = 'video_createtime:'

    @classmethod
    def create(cls, video_key, video_createtime, conn=None, *args, **kwargs):
        conn = cls.get_connection()
        conn.zadd(cls.table_name, video_createtime, video_key)


class VideoCreateTimeScore(Model):
    '''
    按照得分排序用的
    tables:
        video_createtime_score:
    type: zset
    detail:
        video:1 483
        video:2 345
    '''

    table_name = 'video_createtime_score:'

    @classmethod
    def create(cls, video_key, video_createtime, score, conn=None, *args, **kwargs):
        conn = cls.get_connection()
        now = datetime.now()
        _delta = now - datetime.utcfromtimestamp(video_createtime)
        hour = int(_delta.total_seconds() / 60)
        real_score = calculate_score(score, hour, 2)
        conn.zadd(cls.table_name, real_score, video_key)


class User(Model):
    '''
    table:
        user:
    type: hash
    detail:
        username: str
    '''

    table_name = 'user:'

    @classmethod
    def create(cls, username, conn=None, *args, **kwargs):
        conn = cls.get_connection(conn=conn)
        user_id = conn.incr(cls.table_name)
        key = '{}{}'.format(cls.table_name, user_id)
        value = {
            'username': username,
        }
        return conn.hmset(key, value)

    @classmethod
    def generate_data(cls, n=1, conn=None, *args, **kwargs):
        conn = cls.get_connection(conn)
        for i in xrange(n):
            username = faker_factory.user_name()
            cls.create(username, conn=conn)


class Video(Model):
    '''
    tables:
        video:1
        video:2
    type: hash
    detail:
        title: str
        url: (or ccid someting) str
        poster: int
        create_time: float
    '''
    table_name = 'video:'

    @classmethod
    def create(cls, video_id, title,
            url, poster_id, create_time,
            conn=None, *args, **kwargs):
        conn = cls.get_connection(conn=conn)
        key = '{}{}'.format(cls.table_name, video_id)
        value = {
            'title': title,
            'url': url,
            'poster': poster_id,
            'create_time': create_time,
            'votes': 0,
            'unvotes': 0,
        }
        # 创建video对象
        conn.hmset(key, value)
        # 时间排序添加对象
        VideoCreateTime.create(key, create_time, conn)
        # 得分排序添加对象
        VideoScore.create(key, 0, conn)
        # 时间得分排序添加对象
        VideoCreateTimeScore.create(key, create_time, 0, conn)

    @classmethod
    def generate_data(cls, n=1, conn=None, poster_id_range=None, *args, **kwargs):
        conn = cls.get_connection(conn=conn)
        if poster_id_range:
            pmin, pmax = poster_id_range
        for i in xrange(n):
            video_id = conn.incr(cls.table_name)
            url = faker_factory.url()
            title = faker_factory.text()
            if not poster_id_range:
                poster_id = faker_factory.random_int()
            else:
                poster_id = faker_factory.random_int(min=pmin, max=pmax)
            create_time = time.mktime(faker_factory.date_time().timetuple())
            cls.create(video_id, title, url, poster_id, create_time, conn)

    @classmethod
    def get_videos(cls, page, per_page=20,
            order_table=VideoScore.table_name, conn=None, *args, **kwargs):
        start = (page - 1) * per_page
        end = start + per_page - 1
        ids = conn.zrevrange(order_table, start, end)
        videos = []
        for id in ids:
            video = conn.hgetall(id)
            video['id'] = id
            videos.append(video)
        return videos


class VideoVote(Model):
    '''
    tables:
        video_vote:1
        video_vote:2
    type: set
    detail:
        user:1
        user:2
    '''
    table_name = 'video_vote:'
    score = 1

    @classmethod
    def vote(cls, video_id, user_id, conn=None, *args, **kwargs):
        conn = cls.get_connection()
        key = '{}{}'.format(cls.table_name, video_id)
        video_key = '{}{}'.format(Video.table_name, video_id)
        unvote_key = '{}{}'.format(VideoUnVote.table_name, video_id)
        # 没投票
        if not conn.sismember(key, user_id):
            conn.sadd(key, user_id)
            conn.hincrby(video_key, 'votes', 1)
            VideoScore.add(video_key, cls.score)
        # 如果踩过
        if conn.sismember(unvote_key, user_id):
            conn.srem(unvote_key, user_id)
            conn.hincrby(video_key, 'unvotes', -1)
            VideoScore.reduce(video_key, VideoUnVote.score)


class VideoUnVote(Model):
    '''
    tables:
        video_unvote:1
        video_unvote:2
    type: set
    detail:
        user:1
        user:2
    '''
    table_name = 'video_unvote:'
    score = -1

    @classmethod
    def unvote(cls, video_id, user_id, conn=None, *args, **kwargs):
        conn = cls.get_connection()
        key = '{}{}'.format(cls.table_name, video_id)
        vote_key = '{}{}'.format(VideoVote.table_name, video_id)
        video_key = '{}{}'.format(Video.table_name, video_id)
        # 没踩过
        if not conn.sismember(key, user_id):
            conn.sadd(key, user_id)
            conn.hincrby(video_key, 'unvotes', 1)
            VideoScore.add(video_key, cls.score)
        # 如果彩过
        if conn.sismember(vote_key, user_id):
            conn.srem(vote_key, user_id)
            conn.hincrby(video_key, 'votes', -1)
            VideoScore.reduce(video_key, VideoVote.score)
