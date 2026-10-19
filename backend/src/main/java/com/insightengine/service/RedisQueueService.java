package com.insightengine.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class RedisQueueService {

    private static final String DOCUMENT_QUEUE = "document:queue";
    private final RedisTemplate<String, Object> redisTemplate;

    public void enqueueDocumentJob(Map<String, Object> job) {
        log.info("Enqueuing document job: {}", job);
        redisTemplate.opsForList().leftPush(DOCUMENT_QUEUE, job);
    }
}
