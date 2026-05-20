# RFC #0001 — PATCH 시맨틱 표준화

## Summary

`ch-proto-public`의 patch-equivalent request 메시지(현재 `Update*Request` 5개 + `Patch*Request` 2개)의 partial update 시맨틱을 **FieldMask + Body 패턴**(`Patch*Request + Body + update_mask`, AIP-134/161 + RFC 7396)으로 일괄 표준화한다.

## 문제

QA e2e(2026-04-17) 결함 #2: `updatePlugin(name만 변경)` 호출 시 미전송 scalar 필드가 `0`/`false`로 reset되어 운영 데이터 손실.

**원인**: proto3 wire format은 scalar의 zero value와 미설정을 구분 못 함. cht-open-api가 nil 포인터로 보존한 partial update 정보가 ch-proto-public 메시지에서 손실됨.

**범위**: plugin뿐 아니라 다른 6개 patch-equivalent 메시지(`PatchUser` bool 4개, `PatchWebhook` string 4개 등)에도 같은 결함 잠재. 단발 fix가 아닌 **일관 표준** 필요.

## 호출 흐름 (FieldMask는 internal-only)

```
[Customer]                                                 [cht-open-api]                                      [ch-proto-public]                          [ch-dropwizard]
HTTP PATCH /open/plugins/{id}                  →   PluginPatchInput (각 필드 *T)                →    PatchPluginRequest{body, update_mask}    →    PluginsResource
{ "labelButton": true }                              if input.X != nil {                                       (proto3 + FieldMask)                              FieldMaskUtil.merge(...)
                                                       body.X = *input.X;
                                                       mask = append(mask, "label_button")
                                                     }
```

**Customer는 OpenAPI JSON Merge Patch만 본다**. `update_mask`/FieldMask는 cht-open-api ↔ ch-dropwizard 사이의 internal protocol detail. 외부 ergonomics 가중치는 낮고, **internal contract 품질**(일관성/표준)이 의사결정 기준.

## 결정: 옵션 B (FieldMask + Body)

```protobuf
message PatchPluginRequest {
  string plugin_id = 1 [(buf.validate.field).required = true];
  string channel_id = 2 [(buf.validate.field).required = true];

  PatchPluginBody body = 3 [(buf.validate.field).required = true];

  google.protobuf.FieldMask update_mask = 4 [
    (buf.validate.field).required = true,
    (buf.validate.field).cel = {
      id: "field_mask.non_empty"
      message: "update_mask must contain at least one path"
      expression: "size(this.paths) > 0"
    }
  ];

  message PatchPluginBody {
    string name = 1;
    bool label_button = 2;
    int32 desk_margin_x = 3;
    repeated string url_white_list = 4;
    map<string, string> i18n_map = 5;
    // ...
  }
}
```

시맨틱:
- `update_mask.paths`에 포함된 필드만 적용
- mask에 없는 필드 → 변경 안 함
- 모든 필드 타입(scalar/string/repeated/map) 균일 적용

### 옵션 비교 (요약)

| 옵션 | 적용 가능 | v1 일관 | AIP/RFC | `.claude/rules/` |
|---|---|---|---|---|
| A. proto3 `optional` | scalar/string만 | ❌ | ❌ | 예외 단서 필요 |
| **B. FieldMask + Body** | **모든 필드 균일** | **✅** | **AIP-134/161, RFC 7396** | **변경 없음** |
| C. Wrapper types | scalar만 | ❌ | △ | 없음 |

**옵션 A 한계**: proto3 `optional`은 scalar/string에만 적용 가능하고 `repeated`/`map`(예: `url_white_list`, `i18n_map`)에는 적용 안 됨. 같은 메시지 안에서 필드 타입별로 partial update 시맨틱이 갈리는 문제 발생.

**proto3 `optional`/`required` 키워드 비사용 컨벤션**: `.claude/rules/protovalidate.md`에 "키워드 사용 금지, 모든 검증은 buf.validate로" 규칙 존재 (proto2/3 간 키워드 의미 변동 이력 때문). 옵션 A 채택 시 이 규칙에 patch-only 예외 단서 필요.

### 채택 근거

1. **Customer 영향 없음** — proto는 internal contract, customer는 OpenAPI PATCH 그대로 사용
2. **v1 ch-proto와 일관** — ch-dropwizard `ProtoPatch` 유틸리티 재사용 가능
3. **모든 필드 타입 균일** 처리 (scalar/repeated/map 무차별)
4. **AIP-134/161 + RFC 7396 표준 준거**
5. **명명 `Patch*`로 통일** — HTTP PATCH와 정합, v1 일치
6. **`.claude/rules/` 규칙 변경 불필요**

## 세부 결정 사항

### Empty `update_mask` 정책 — reject (422)

AIP-161 권장: "If the field mask is empty, the request should be considered invalid."

**proto-level 검증 + handler-level 방어 심층**:

1. **proto-level**: `(buf.validate.field).required = true` (FieldMask 메시지 presence) + CEL `size(this.paths) > 0` (paths 비어있지 않음). buf.validate가 사전 422 거부 — handler 도달 전 차단.
   - 참고: `required = true`만으로는 FieldMask 메시지의 presence만 검증되고 `paths` 내부는 검증 안 됨. CEL 보강 필수.

2. **handler-level**: `ch-dropwizard/libs/protobuf/ProtoPatch.java`가 이미 `mask.getPathsCount() == 0` 체크 + `InvalidProtobufMessageException` 던짐. v1 패턴 그대로 답습.

### Path naming 규약 — `snake_case`

근거 일치:
- protobuf style guide: 필드 이름은 `lower_snake_case`
- AIP-161: "Field names in field masks must use the proto convention for field naming"
- v1 ch-proto `PatchPluginRequest.PatchPluginBody`: 모든 필드 `snake_case`
- ch-dropwizard `FieldMaskUtil.merge()`/`FieldMaskUtil.isValid()`: protobuf descriptor 기반 매칭 → snake_case 필수

변환 책임:
- Customer JSON 요청 (camelCase): `{"labelButton": true}`
- cht-open-api 내부: Go field → snake_case 변환 후 mask에 추가 (`mask = ["label_button"]`)
- proto/ch-dropwizard: snake_case path로 처리

### Invalid path 처리 — `ProtoPatch` 답습 + Core API 응답 표준 변환

기존 `ch-dropwizard/libs/protobuf/ProtoPatch.java:35-42`:

```java
if (!FieldMaskUtil.isValid(patch.getDescriptorForType(), mask)) {
  throw new InvalidProtobufMessageException("Invalid patch message: update mask is not valid for body");
}
if (mask.getPathsCount() == 0) {
  throw new InvalidProtobufMessageException("Invalid patch message: empty update mask");
}
```

`FieldMaskUtil.isValid(descriptor, mask)`가 descriptor에 없는 path 거부.

**문제**: `InvalidProtobufMessageException` → `BaseExceptionMapper` → 400 + legacy `ErrorView`. Core API 표준 `ErrorResponse`와 포맷 다름.

**해결**: handler에서 try-catch로 `CoreApiException.validationFailed()` 변환. 또는 `CoreApiGuard.applyPatchOrThrow(...)` 같은 헬퍼로 추상화 (BEAPI-6466에서 추가한 `requireNonEmptyMessageContent` 패턴과 일관).

```java
public static void applyPatchOrThrow(ProtoPatchTemplate template, ...) {
  try {
    template.create(...).applyTo(target);
  } catch (InvalidProtobufMessageException e) {
    throw CoreApiException.validationFailed("invalid update_mask: " + e.getMessage());
  }
}
```

### Body 필드의 null vs default — v1과 동일 한계 (수용)

proto3 scalar body 필드는 미설정과 zero value 구분 불가.

mask에 `["label_button"]` 포함 + body의 `label_button = false`일 때:
- "false로 set 의도" 또는 "값 누락(default zero)" 둘 다 가능
- 운영상 차이가 없으면 무방 (bool, int 등)
- string에서 `null`(clear) vs `""`(empty) 구분이 의미 있는 경우 별도 처리 필요

**컨벤션**: mask에 path가 있으면 body의 값을 그대로 set (default일지라도 명시적 의도로 해석). v1과 동일.

customer가 명시적 clear를 보내고 싶으면 cht-open-api가 `null` 입력 → body의 default 값(`""`/`0`/`false`)으로 변환. 대부분의 경우 차이 없음.

## 잔여 검토 (이행 단계에서 처리)

- **Nested path 지원**: AIP-161은 `body.appearance.theme` 같은 nested path 지원 권장. 7개 메시지가 거의 flat 구조라 **top-level path만 우선 지원**, nested는 필요 시점에 확장.
- **Field-level 권한**: mask path별로 다른 권한이 필요한 경우 ch-dropwizard 핸들러에서 처리. 본 RFC scope 밖.
- **cht-open-api boilerplate**: 7개 메시지 × 평균 8~20개 필드 nil 체크 반복. 우선 손코딩(PR #60 패턴 답습), 후속으로 generic helper 검토 — 별개 이슈.
- **`protoc-gen-openapi` FieldMask 렌더링**: 보통 `repeated string`으로 단순 매핑. customer에게는 cht-open-api 자체 OpenAPI 노출하므로 영향 작음. 한 번 실측 후 RFC 갱신.

## 마이그레이션 영향

**Breaking change**:
- 메시지 이름 변경 (`Update*Request` → `Patch*Request`)
- 메시지 구조 변경 (필드를 `Body` nested로 이동)
- `skip-breaking` 라벨 필요 (buf breaking 검사)

**영향 범위**:
- ✅ Customer: 영향 없음 (OpenAPI는 그대로, cht-open-api가 변환)
- ⚠️ cht-open-api: 모든 `pkg/dwcoreapi/*.go`의 Update 함수 호출부 갱신 필요 (동시)
- ⚠️ ch-dropwizard: 5개 핸들러(`PluginsResource.update*` 등) 재작성 필요 (동시)

**배포 순서**:
1. ch-proto-public PR (#60) 머지
2. cht-open-api + ch-dropwizard에서 submodule bump + 코드 동시 갱신
3. 두 서비스 거의 동시 배포 (어차피 customer 영향 없음)

## 이행 계획

1. **PR #60** (FieldMask 일괄 표준화, @pjy1368 작성) 머지
2. **PR #56** (plugin optional 응급 backup) close
3. **cht-open-api**: `pkg/dwcoreapi/*.go` Update 함수 호출부 갱신 (camelCase → snake_case 변환 포함)
4. **ch-dropwizard**: 5개 핸들러 FieldMask 기반으로 재작성 (`ProtoPatch` 답습) + `CoreApiGuard.applyPatchOrThrow` 헬퍼 추가

## References

- Google AIP-134 [Standard methods: Update](https://google.aip.dev/134)
- Google AIP-161 [Field masks](https://google.aip.dev/161)
- RFC 7396 [JSON Merge Patch](https://datatracker.ietf.org/doc/html/rfc7396)
- v1 `coreapi/v1/service/plugin.proto` — `PatchPluginRequest` 레퍼런스 구현
- `ch-dropwizard/src/main/java/io/channel/api/libs/protobuf/ProtoPatch.java` — invalid/empty mask 처리 유틸리티
- QA 결과: `ch-dropwizard/docs/open-api-migration/qa-e2e-results-2026-04-17.md` (결함 #2)
