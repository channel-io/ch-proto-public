# buf.validate (protovalidate) 사용 규칙

모든 proto 파일(`coreapi/model/`, `coreapi/service/`)에서 필드 검증에 `buf.validate`를 사용한다.

## import

```protobuf
import "buf/validate/validate.proto";
```

## 기본 원칙

- `optional`/`required` 키워드는 사용하지 않는다 (proto3 기본 동작에 맡긴다)
- 필수/길이/패턴 등 모든 검증은 `buf.validate` 어노테이션으로 표현한다

### 예외 (잠정): PATCH/Update Request의 scalar nullable 필드

> **주의**: 본 예외는 RFC(`docs/rfc/0001-patch-semantics.md`) 결정에 따라 변경되거나 폐기될 수 있다. RFC 합의 전까지의 잠정 단서.

부분 업데이트(PATCH 시맨틱)를 표현해야 하는 `Update*Request`의 scalar 필드(bool/int/float)는 `optional` 키워드를 허용한다. proto3에서 scalar는 zero value(`0`/`false`)와 미전송을 구분할 방법이 없어, 미전송 시 zero value로 덮어쓰는 운영 데이터 손실이 발생하기 때문.

```protobuf
message UpdatePluginRequest {
  // ...
  // +kubebuilder:validation:Nullable
  optional bool label_button = 5;        // hasLabelButton() 사용 가능

  // +kubebuilder:validation:Nullable
  optional int32 desk_margin_x = 10;     // hasDeskMarginX() 사용 가능

  // +kubebuilder:validation:Nullable
  optional float run_rate = 19;          // hasRunRate() 사용 가능
}
```

적용 범위:
- 대상은 `Update*Request`의 **scalar nullable 필드**에 한함 (string/enum/message는 zero/UNSPECIFIED로 구분 가능하므로 불필요)
- 응답 메시지나 모델 정의(`coreapi/model/`)에는 적용하지 않는다
- `+kubebuilder:validation:Nullable` marker는 그대로 유지

## required 필드

```protobuf
string channel_id = 1 [(buf.validate.field).required = true];
```

## CEL 표현식

복합 검증 로직은 CEL(Common Expression Language)로 작성한다.

```protobuf
string name = 2 [
  (buf.validate.field).cel = {
    id: "string.minLen"
    message: "value must be at least 1 character"
    expression: "size(this) >= 1"
  },
  (buf.validate.field).cel = {
    id: "string.maxLen"
    message: "value must be no more than 30 characters"
    expression: "size(this) <= 30"
  },
  (buf.validate.field).required = true
];
```

- `id`: 검증 규칙 식별자. `string.minLen`, `string.maxLen`, `int32.gte` 등
- `message`: 검증 실패 시 반환할 메시지
- `expression`: CEL 표현식

## 정규식 패턴

```protobuf
string name = 2 [
  (buf.validate.field).string.pattern = "^[^@#$%:/]+$"
];
```

## 검증 없는 필드

검증 제약이 없는 필드에는 `buf.validate` 어노테이션을 붙이지 않는다.

```protobuf
string color = 5;
```

## kubebuilder marker와의 관계

proto에서는 kubebuilder marker(OpenAPI 문서 생성용)와 buf.validate(런타임 검증용)를 **함께** 작성한다.
검증 가능한 항목은 양쪽 모두에 표현해야 한다.

| kubebuilder marker | buf.validate 대응 |
|---|---|
| `+kubebuilder:validation:Required` | `(buf.validate.field).required = true` |
| `+kubebuilder:validation:MinLength=N` | CEL: `size(this) >= N` |
| `+kubebuilder:validation:MaxLength=N` | CEL: `size(this) <= N` |
| `+kubebuilder:validation:Minimum=N` | CEL: `this >= N` |
| `+kubebuilder:validation:Maximum=N` | CEL: `this <= N` |
| `+kubebuilder:validation:Pattern="regex"` | `(buf.validate.field).string.pattern` |
| `+kubebuilder:validation:Nullable` | 대응 없음 (marker만 사용) |
| `+kubebuilder:example="value"` | 대응 없음 (marker만 사용) |
| `+kubebuilder:default="value"` | 대응 없음 (marker만 사용) |
