# RFC #0001 — PATCH 시맨틱 표준화

| | |
|---|---|
| **Status** | Draft |
| **Authors** | @terry (devsungtae), @pjy1368 |
| **Created** | 2026-05-12 |
| **Linear** | BEAPI-5924 (의사결정), BEAPI-6479 (본 문서), BEAPI-6463 / BEAPI-6464 (후보 PR 트랙) |
| **Related PRs** | [#56](https://github.com/channel-io/ch-proto-public/pull/56) (Draft, optional), [#60](https://github.com/channel-io/ch-proto-public/pull/60) (Draft, FieldMask), [#58](https://github.com/channel-io/ch-proto-public/pull/58) (closed) |

## Summary

`ch-proto-public`의 patch-equivalent request 메시지(현재 `Update*Request` 5개 + `Patch*Request` 2개)의 partial update 시맨틱을 어떻게 표현할지 표준화한다. **추천: FieldMask + Body 패턴(`Patch*Request + Body + update_mask`) 일괄 채택**. AIP-134/161 + RFC 7396 표준 준거, v1 ch-proto와 일관, 모든 필드 타입 균일 처리.

## 1. 배경

### QA 결함

QA e2e(2026-04-17) 결함 #2: `updatePlugin(name만 변경)` 요청 시 미전송 scalar 필드가 `0`/`false`로 리셋되어 운영 데이터가 덮어써짐.

`PluginsResource.updatePlugin` (`/admin/core/pub/plugins/updatePlugin`)의 현재 구현:

```java
p.setLabelButton(req.getLabelButton());    // proto3 false vs 미설정 구분 불가
p.setDeskMarginX(req.getDeskMarginX());    // proto3 0 vs 미설정 구분 불가
p.setRunRate(req.getRunRate());
// ... 8개 scalar 모두 무조건 setter 호출 → PUT 시맨틱 ❌
```

### 일반화 필요성

같은 결함이 다른 7개 patch-equivalent 메시지에도 잠재:

| 메시지 | 위험 필드 |
|---|---|
| `UpdatePluginRequest` | scalar 8개 (bool 4개 + int32 4개 + float 1개) |
| `PatchUserRequest` | bool 4개 (`blocked`, `unsubscribe_email/texting/app_push`) |
| `PatchWebhookRequest` | string 4개 (빈 값 = clear vs unchanged 모호) |
| 그 외 (UserChat, ChatTag, Group, GroupByName) | 각자 scalar/string 분포 |

plugin만 단발 처리로는 일관성 결여. **전체 patch-equivalent 메시지에 일관 패턴 적용 필요**.

## 2. 시스템 호출 흐름

```
[Customer (고객사 개발자)]
     │ HTTP PATCH /open/plugins/{pluginId}
     │ body: { "labelButton": true, "deskMarginX": 20 }   ← 변경할 필드만 (JSON Merge Patch 스타일)
     ▼
[cht-open-api]   ← OpenAPI 노출, codegen 기반
     │ - Customer-facing OpenAPI: HTTP PATCH method, *PatchInput (각 필드 oneOf [type, "null"])
     │ - Go 모델: 각 필드 *T (nil pointer)
     │ - cht-open-api internal 변환:
     │     if input.X != nil { req.X = *input.X }  ← nil 정보 보존 시도
     ▼
[ch-proto-public/coreapi.service.UpdatePluginRequest]
     │ ⚠️ proto3 scalar wire format은 zero value vs 미설정 구분 불가
     │ → cht-open-api 측의 nil 정보가 직렬화 시 손실
     ▼
[ch-dropwizard /admin/core/pub/plugins/updatePlugin]
       - req.getLabelButton() → 항상 boolean (info 손실)
       - 모든 setter 무조건 호출 → PUT 시맨틱 ❌ 운영 데이터 손실
```

**결함의 본질**: proto3 wire format이 cht-open-api ↔ ch-dropwizard 사이에서 partial update 정보(어느 필드가 set됐는지)를 보존하지 못함. ch-proto-public 메시지가 이를 어떻게 표현할지가 핵심.

## 3. 핵심 통찰: customer는 proto를 안 봄

- Customer가 직접 보는 contract: **cht-open-api의 OpenAPI 스펙** (PATCH 메서드, `*PatchInput`)
- Customer의 SDK: OpenAPI codegen 결과물 — proto는 보이지 않음
- 따라서 ch-proto-public의 메시지 형태/명명은 **customer 영향 없음**
- ch-proto-public 결정의 핵심 가치는 **internal contract 품질** (cht-open-api ↔ ch-dropwizard 일관성, 유지보수성, 표준 준거)

이 통찰이 옵션 선택의 가중치를 좌우한다.

## 4. 현재 명명 불일치

ch-proto-public:

* `Update*`: UserChat, Plugin, ChatTag, Group, GroupByName (5개)
* `Patch*`: Webhook, User (2개)

v1 ch-proto (참고): **모두 `Patch*Request + Body + FieldMask` 일관**.

명명도 시맨틱도 ch-proto-public 자체적으로 혼란이며 v1과도 불일치.

## 5. 후보 옵션

### 옵션 A — proto3 `optional` 키워드

```protobuf
message UpdatePluginRequest {
  string plugin_id = 1 [(buf.validate.field).required = true];
  string channel_id = 2 [(buf.validate.field).required = true];

  optional bool label_button = 5;
  optional int32 desk_margin_x = 10;
  optional float run_rate = 19;

  string label_button_text = 6;             // string은 proto3 spec상 optional 불필요 (Java hasXxx 자동)
  repeated string url_white_list = 19;      // ⚠️ optional 적용 불가
  map<string, string> i18n_map = 7;         // ⚠️ optional 적용 불가
}
```

* 장점: cht-open-api Go 코드 변경 거의 없음, hasXxx() 단순
* 단점:
  - **`repeated`/`map`에 적용 불가** (proto3 spec) → 정책 비대칭
  - `.claude/rules/protovalidate.md`의 "optional 미사용" 규칙과 충돌
  - v1 ch-proto와 다른 패턴
  - "필드가 set인지 unset인지"와 "필드를 clear 의도"의 구분이 약함 (scalar zero가 의미 있는 값과 충돌)

### 옵션 B — FieldMask + Body (`Patch*Request` rename) ← 추천

```protobuf
message PatchPluginRequest {
  string plugin_id = 1 [(buf.validate.field).required = true];
  string channel_id = 2 [(buf.validate.field).required = true];

  PatchPluginBody body = 3 [(buf.validate.field).required = true];
  google.protobuf.FieldMask update_mask = 4 [(buf.validate.field).required = true];

  message PatchPluginBody {
    string name = 1;
    bool label_button = 2;
    int32 desk_margin_x = 3;
    float run_rate = 4;
    repeated string url_white_list = 5;
    map<string, string> i18n_map = 6;
    // ...
  }
}
```

시맨틱(RFC 7396 / AIP-134/161):

* `update_mask` path에 포함된 필드: body 값 적용 (value면 set, null이면 clear)
* `update_mask`에 없는 필드: 변경 안 됨

* 장점:
  - **모든 필드 타입(scalar/repeated/map/enum/message) 균일 처리**
  - **v1 ch-proto와 일관** → ch-dropwizard 핸들러 v1 코드 답습 가능
  - AIP-134/161 + RFC 7396 표준 준거
  - `.claude/rules/protovalidate.md` 규칙 변경 불필요
  - `Patch*` 이름이 HTTP PATCH 시맨틱과 정합
  - clear vs unchanged 구분 명시적
* 단점:
  - cht-open-api Go 변환 코드 boilerplate 증가 (~2x lines)
  - body 한 단계 nesting 추가
  - 메시지 이름 변경 (`Update*` → `Patch*`) — definition-level breaking (단 cht-open-api만 영향)

### 옵션 C — Wrapper types (`google.protobuf.BoolValue` 등)

```protobuf
message UpdatePluginRequest {
  google.protobuf.BoolValue label_button = 5;
  google.protobuf.Int32Value desk_margin_x = 10;
  google.protobuf.StringValue label_button_text = 6;
  // repeated/map은 여전히 처리 어려움
}
```

* 장점: proto3 well-known types, `optional` 키워드 미사용
* 단점:
  - 코드 verbose (`request.getX().getValue()`)
  - **`repeated`/`map`은 여전히 비대칭** (옵션 A와 동일 한계)
  - `protoc-gen-openapi`의 wrapper 처리가 도구마다 다름

## 6. 의사결정 기준 및 가중치

| 기준 | 가중치 | 근거 |
|---|---|---|
| Customer ergonomics (OpenAPI 측면) | 🔵 매우 낮음 | proto는 internal contract — customer는 OpenAPI만 봄 |
| AIP/RFC 표준 준거 | 🔴 높음 | 향후 외부 협업/문서화 시 정당화 기반 |
| v1 ch-proto 일관성 | 🔴 높음 | ch-dropwizard 핸들러 코드 답습, 마이그레이션 컨텍스트 |
| 모든 필드 타입 균일 처리 | 🔴 높음 | repeated/map 제약 해소, 미래 confusion 방지 |
| cht-open-api boilerplate | 🟡 중간 | 한 번 패턴 만들면 7개 메시지에 균일 적용 |
| ch-dropwizard 개발 부담 | 🟢 낮음 | 옵션 B 채택 시 v1 패턴 답습 |
| `.claude/rules/` 변경 | 🟡 중간 | 옵션 A는 예외 단서 필요, B/C는 변경 없음 |

## 7. 결정: 옵션 B 채택

### 요약 비교

| 기준 | A. optional | **B. FieldMask** | C. Wrapper |
|---|---|---|---|
| 외부 customer ergonomics | ⭐⭐⭐⭐⭐ (불필요) | ⭐⭐⭐ | ⭐⭐ |
| AIP/RFC 표준 준거 | ❌ | ✅ AIP-134/161, RFC 7396 | △ proto well-known |
| v1 ch-proto 일관성 | ❌ | ✅ | ❌ |
| 모든 필드 타입 균일 | ❌ scalar/string만 | ✅ | ❌ scalar만 |
| `.claude/rules/` 변경 | 예외 단서 필요 | 없음 | 없음 |
| ch-dropwizard 핸들러 | 새 패턴 | v1 답습 | 새 패턴 |
| clear vs unchanged 구분 | 약함 | 명시적 | scalar만 |

### 채택 근거

1. **외부 customer 영향 없음** — proto는 internal contract이며 OpenAPI 스펙(`*PatchInput`)이 외부 ergonomics를 이미 충분히 담당
2. **v1 ch-proto와 일관** — 마이그레이션 컨텍스트에서 자연스럽고, ch-dropwizard 핸들러 코드 재사용 가능
3. **모든 필드 타입 균일** — scalar/repeated/map 무차별 적용, 미래 필드 추가 시 confusion 없음
4. **AIP-134/161 + RFC 7396 표준 준거** — 외부 협업/문서화 시 정당화 강력
5. **명명 일관성** — `Patch*` 이름이 HTTP PATCH 시맨틱과 정합, v1과 일치
6. **`.claude/rules/` 변경 불필요** — `optional` 미사용 원칙 유지

유일한 단점인 cht-open-api boilerplate는 헬퍼 함수 또는 codegen으로 추상화 가능(7개 메시지에 균일 패턴).

## 8. 이행 계획

### Phase 1: 본 RFC 머지

* RFC 문서를 `docs/rfc/0001-patch-semantics.md`로 머지 (BEAPI-6479)
* pjy1368 리뷰 + 합의

### Phase 2: ch-proto-public 적용

* **PR #60** (BEAPI-6464, @pjy1368 작성) 머지 — 7개 메시지 일괄 변환
* **PR #56** (BEAPI-6463, optional 응급 backup) close
* 명명: `Update*Request` → `Patch*Request` (5개)

### Phase 3: cht-open-api 적용

* `pkg/dwcoreapi/*.go` updateX 함수의 호출부 변환:
  - 기존: `if input.X != nil { req.X = *input.X }`
  - 변경: `if input.X != nil { body.X = *input.X; mask = append(mask, "X") }`
* Boilerplate 추상화를 위한 헬퍼 함수 검토 (선택, 별개 작업)

### Phase 4: ch-dropwizard 적용

* `PluginsResource.updatePlugin` 등 5개 핸들러를 FieldMask 기반 처리로 변환:
  - v1 ch-dropwizard의 `PatchPluginRequest` 핸들러 패턴 답습 (v1 코드 기반)
  - path 순회 + switch 또는 path → setter 매핑 헬퍼

BEAPI-5926 후속 작업의 일부로 진행.

## 9. Migration breaking change 평가

* **proto definition-level breaking**: 메시지 이름 변경 (`Update*Request` → `Patch*Request`)
* **wire-level breaking**: 메시지 구조 변경 (필드를 `Body` nested로 이동)
* **영향 범위**:
  - Customer (외부 SDK): 영향 없음 (OpenAPI는 그대로, cht-open-api가 내부 변환)
  - cht-open-api: 동시 갱신 필요 (Phase 3)
  - ch-dropwizard: 동시 갱신 필요 (Phase 4)
* **`skip-breaking` 라벨**: ch-proto-public CI의 buf breaking 검사 우회 필요

배포 순서: ch-proto-public PR 머지 → cht-open-api + ch-dropwizard PR 동시 머지/배포.

## 10. `.claude/rules/` 영향

옵션 B 채택 시 변경 **없음**:

* `model.md`/`protovalidate.md`의 `optional` 미사용 원칙 유지
* service 메시지 명명 규칙은 본 RFC에서 `Patch*` 패턴을 표준으로 명시
* 향후 새 mutation API 추가 시 본 패턴 따르도록 `.claude/rules/service.md`에 단서 추가 검토 (별도 PR)

## 11. Open Questions

### Q1. cht-open-api boilerplate 추상화 깊이

`if input.X != nil { body.X = *input.X; mask = append(mask, "X") }` 패턴이 매 필드마다 반복됨. 헬퍼 함수 또는 generic으로 추상화 가능하나 cht-open-api 측 별개 작업으로 검토 필요. 본 RFC scope 밖.

### Q2. Field path 명명

`update_mask` 안에 들어가는 path 문자열의 정확한 형식:

* protobuf 표준: snake_case (`label_button`)
* JSON: camelCase (`labelButton`)

protovalidate/protoc-gen-openapi가 path 변환을 어떻게 처리하는지 실측 필요. 본 RFC는 표준 snake_case path를 따른다고 가정.

### Q3. `update_mask` validation

`(buf.validate.field).required = true`를 mask에 적용 권장 (v1 ch-proto와 동일). 단 빈 mask 허용 정책(no-op vs reject)은 별도 결정 필요.

## 12. References

* Google AIP-134 [Standard methods: Update](https://google.aip.dev/134)
* Google AIP-161 [Field masks](https://google.aip.dev/161)
* RFC 7396 [JSON Merge Patch](https://datatracker.ietf.org/doc/html/rfc7396)
* RFC 5789 [PATCH Method for HTTP](https://datatracker.ietf.org/doc/html/rfc5789)
* v1 ch-proto `coreapi/v1/service/plugin.proto` (`PatchPluginRequest` 레퍼런스 구현)
* QA 결과: `ch-dropwizard/docs/open-api-migration/qa-e2e-results-2026-04-17.md` (결함 #2)
