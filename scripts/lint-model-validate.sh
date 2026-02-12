#!/usr/bin/env bash
#
# coreapi/model/*.proto 파일에서 kubebuilder marker가 있으면
# 대응하는 buf.validate 어노테이션이 같은 필드에 존재하는지 검증한다.
#
set -euo pipefail

errors=0

lint_file() {
  local file="$1"
  local comment_block=""
  local comment_start_line=0
  local lineno=0

  while IFS= read -r line; do
    lineno=$((lineno + 1))

    # 주석 줄 수집
    if [[ "$line" =~ ^[[:space:]]*//.* ]]; then
      if [[ -z "$comment_block" ]]; then
        comment_start_line=$lineno
      fi
      comment_block+="$line"$'\n'
      continue
    fi

    # 주석이 아닌 줄 → 필드 선언인지 확인
    if [[ -n "$comment_block" ]]; then
      # 필드 선언 + 이어지는 어노테이션 블록까지 수집
      local field_block="$line"
      # 여러 줄에 걸친 [...] 어노테이션 수집
      if [[ "$line" =~ \[ ]] && ! [[ "$line" =~ \] ]]; then
        while IFS= read -r next_line; do
          lineno=$((lineno + 1))
          field_block+=$'\n'"$next_line"
          if [[ "$next_line" =~ \] ]]; then
            break
          fi
        done
      fi

      check_field "$file" "$comment_start_line" "$comment_block" "$field_block"
      comment_block=""
    fi
  done < "$file"
}

check_field() {
  local file="$1"
  local start_line="$2"
  local comments="$3"
  local field="$4"

  # Required
  if echo "$comments" | grep -q '+kubebuilder:validation:Required'; then
    if ! echo "$field" | grep -q 'required = true'; then
      echo "$file:$start_line: +kubebuilder:validation:Required 에 대응하는 (buf.validate.field).required = true 누락"
      errors=$((errors + 1))
    fi
  fi

  # MinLength=N
  local min_match
  min_match=$(echo "$comments" | sed -n 's/.*+kubebuilder:validation:MinLength=\([0-9]*\).*/\1/p' | head -1)
  if [[ -n "$min_match" ]]; then
    if ! echo "$field" | grep -q "size(this) >= $min_match"; then
      echo "$file:$start_line: +kubebuilder:validation:MinLength=$min_match 에 대응하는 CEL size(this) >= $min_match 누락"
      errors=$((errors + 1))
    fi
  fi

  # MaxLength=N
  local max_match
  max_match=$(echo "$comments" | sed -n 's/.*+kubebuilder:validation:MaxLength=\([0-9]*\).*/\1/p' | head -1)
  if [[ -n "$max_match" ]]; then
    if ! echo "$field" | grep -q "size(this) <= $max_match"; then
      echo "$file:$start_line: +kubebuilder:validation:MaxLength=$max_match 에 대응하는 CEL size(this) <= $max_match 누락"
      errors=$((errors + 1))
    fi
  fi

  # Minimum=N
  local min_val
  min_val=$(echo "$comments" | sed -n 's/.*+kubebuilder:validation:Minimum=\([0-9]*\).*/\1/p' | head -1)
  if [[ -n "$min_val" ]]; then
    if ! echo "$field" | grep -q "this >= $min_val"; then
      echo "$file:$start_line: +kubebuilder:validation:Minimum=$min_val 에 대응하는 CEL this >= $min_val 누락"
      errors=$((errors + 1))
    fi
  fi

  # Maximum=N
  local max_val
  max_val=$(echo "$comments" | sed -n 's/.*+kubebuilder:validation:Maximum=\([0-9]*\).*/\1/p' | head -1)
  if [[ -n "$max_val" ]]; then
    if ! echo "$field" | grep -q "this <= $max_val"; then
      echo "$file:$start_line: +kubebuilder:validation:Maximum=$max_val 에 대응하는 CEL this <= $max_val 누락"
      errors=$((errors + 1))
    fi
  fi

  # Pattern
  if echo "$comments" | grep -q '+kubebuilder:validation:Pattern='; then
    if ! echo "$field" | grep -q 'string.pattern'; then
      echo "$file:$start_line: +kubebuilder:validation:Pattern 에 대응하는 (buf.validate.field).string.pattern 누락"
      errors=$((errors + 1))
    fi
  fi
}

# main
found=0
for file in coreapi/model/*.proto; do
  [[ -f "$file" ]] || continue
  found=1
  lint_file "$file"
done

if [[ $found -eq 0 ]]; then
  echo "No proto files found in coreapi/model/"
  exit 1
fi

if [[ $errors -gt 0 ]]; then
  echo ""
  echo "lint-model-validate: $errors error(s) found"
  exit 1
fi

echo "lint-model-validate: ok"
