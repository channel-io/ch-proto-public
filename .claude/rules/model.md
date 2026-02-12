# Model Proto 작성 규칙

`coreapi/model/` 하위에 도메인 엔티티를 정의할 때 따르는 규칙.

## 왜 주석과 kubebuilder marker를 쓰는가

이 proto 모델은 `cht-open-api` 프로젝트에서 `protoc-gen-openapi` (solo-io)를 통해 OpenAPI 스키마로 자동 변환된다.

- **일반 주석** → OpenAPI `description`
- **kubebuilder marker** → OpenAPI `required`, `nullable`, `minLength`, `maxLength`, `example` 등 validation/메타데이터

즉, proto 주석이 곧 공개 API 문서의 원본이다. 정확하고 충분하게 작성해야 한다.

## 파일 헤더

```protobuf
syntax = "proto3";

package coreapi.model;

option go_package = "github.com/channel-io/ch-proto-public/coreapi/go/model";
option java_multiple_files = true;
option java_package = "io.channel.api.proto.coreapi.model";
```

## 주석 작성

주석은 **description 영역**과 **marker 영역** 두 블록으로 나뉜다. 빈 주석 줄(`//`)로 격리한다.

### description 영역 (→ OpenAPI `description`)

- 모든 message와 필드에 한 줄 이상 작성
- 영문으로 작성
- 필드가 무엇인지, marker로 표현할 수 없는 비즈니스 맥락만 설명 (편집 권한, 동작 조건 등)
- **marker로 표현 가능한 정보는 절대 중복하지 않는다** (글자수, 필수 여부, nullable, 패턴 등)

### marker 영역 (→ OpenAPI validation/메타데이터)

- `+kubebuilder:validation:*` — Required, Nullable, MinLength 등
- `+kubebuilder:example=*` — 예제 값

```protobuf
// Bot display name.                          ← description
// Unique within the channel.                 ← description (계속)
//                                            ← 격리
// +kubebuilder:validation:Required           ← marker
// +kubebuilder:validation:MinLength=1        ← marker
// +kubebuilder:validation:MaxLength=30       ← marker
string name = 3;
```

### Required / Nullable 표현

- Required → `+kubebuilder:validation:Required`
- Nullable → `optional` 키워드 + `+kubebuilder:validation:Nullable`
- `map` 타입은 `optional` 불가 → `+kubebuilder:validation:Nullable` marker만 사용

## kubebuilder marker 목록

| Marker | OpenAPI 매핑 |
|--------|-------------|
| `+kubebuilder:validation:Required` | `required: [field]` |
| `+kubebuilder:validation:Nullable` | `nullable: true` |
| `+kubebuilder:validation:MinLength=N` | `minLength: N` |
| `+kubebuilder:validation:MaxLength=N` | `maxLength: N` |
| `+kubebuilder:validation:Minimum=N` | `minimum: N` |
| `+kubebuilder:validation:Maximum=N` | `maximum: N` |
| `+kubebuilder:validation:Pattern="regex"` | `pattern: regex` |
| `+kubebuilder:validation:MinItems=N` | `minItems: N` |
| `+kubebuilder:validation:MaxItems=N` | `maxItems: N` |
| `+kubebuilder:validation:Enum={A,B,C}` | `enum: [A, B, C]` |
| `+kubebuilder:validation:Format="fmt"` | `format: fmt` |
| `+kubebuilder:example="value"` | `example: value` |
| `+kubebuilder:default="value"` | `default: value` |

## 타입 사용

| 용도 | 타입 |
|------|------|
| 타임스탬프 | `google.protobuf.Timestamp` (import 필요) |
| 다국어 맵 | `map<string, coreapi.model.NameDesc>` |
| 다른 모델 참조 | FQN 사용: `coreapi.model.NameDesc` |

## 필드 번호

- 한번 할당된 필드 번호는 변경하지 않는다 (wire 호환성)
- 삭제된 필드의 번호는 재사용하지 않는다
- 새 필드는 기존 최대 번호 + 1로 추가

## enum 규칙

- 0번 값은 반드시 `_UNSPECIFIED` 접미사 사용: `SORT_ORDER_UNSPECIFIED = 0`
- enum 값 이름은 enum 이름을 접두사로 포함: `SORT_ORDER_ASC`, `SORT_ORDER_DESC`
- enum은 별도 파일 또는 관련 message와 같은 파일에 정의

## 참고 예시

현재 `coreapi/model/bot.proto`가 이 규칙을 따르는 레퍼런스 구현이다.
