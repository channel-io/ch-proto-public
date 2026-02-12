# buf.validate (protovalidate) 사용 규칙

모든 proto 파일(`coreapi/model/`, `coreapi/service/`)에서 필드 검증에 `buf.validate`를 사용한다.

## import

```protobuf
import "buf/validate/validate.proto";
```

## 기본 원칙

- `optional`/`required` 키워드는 사용하지 않는다 (proto3 기본 동작에 맡긴다)
- 필수/길이/패턴 등 모든 검증은 `buf.validate` 어노테이션으로 표현한다

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
    message: "value must be at least 1 characters"
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

model proto에서는 kubebuilder marker(OpenAPI 문서 생성용)와 buf.validate(런타임 검증용)를 **함께** 작성한다.
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
