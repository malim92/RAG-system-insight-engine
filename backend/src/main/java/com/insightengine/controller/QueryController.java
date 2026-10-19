package com.insightengine.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class QueryController {

    private final WebClient aiServiceWebClient;

    @PostMapping("/query")
    public ResponseEntity<?> query(@RequestBody Map<String, String> request) {
        String question = request.get("question");
        String tenantId = request.getOrDefault("tenantId", "default");

        if (question == null || question.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of("error", "question is required"));
        }

        log.info("Query from tenant {}: {}", tenantId, question);

        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> aiResponse = aiServiceWebClient.post()
                    .uri("/query")
                    .bodyValue(Map.of(
                            "question", question,
                            "tenant_id", tenantId
                    ))
                    .retrieve()
                    .bodyToMono(Map.class)
                    .block();

            return ResponseEntity.ok(aiResponse);

        } catch (WebClientResponseException e) {
            // The AI service responded with an error status (4xx/5xx).
            // Propagate BOTH its status code and its body VERBATIM — the
            // body already contains the real, specific error (e.g. Gemini's
            // 503 "high demand" message). Rewriting it here would destroy
            // the information the caller needs.
            log.error("AI service returned {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            return ResponseEntity.status(e.getStatusCode())
                    .body(Map.of("error", e.getResponseBodyAsString(),
                            "code", e.getStatusCode().value()));

        } catch (Exception e) {
            // Connection refused, timeouts, etc. NOTE: some exceptions have
            // a null message (e.g. Netty's ReadTimeoutException), so never
            // concatenate e.getMessage() blindly — fall back to the class name.
            log.error("AI service unreachable", e);
            String detail = (e.getMessage() != null) ? e.getMessage() : e.getClass().getSimpleName();
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(Map.of("error", "AI service unreachable: " + detail));
        }
    }
}
