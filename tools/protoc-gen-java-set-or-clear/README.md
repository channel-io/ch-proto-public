# protoc-gen-java-set-or-clear

This is a protoc plugin that generates Java code with set-or-clear methods for optional fields, and add-all-or-clear methods for repeated fields. The generated Java code contains utility methods that supports conversions of nullable objects and collections to protobuf messages.

For example, given the following protobuf definition:

```proto
message Foo {
  string bar = 1;
  repeated string baz = 2;
}
```

The originally generated Java code will look like:

```java
public class Foo {
  /* ... */

  public static final class Builder {
    /* ... */

    public Builder setBar(String value) { /* ... */ }
    public Builder clearBar() { /* ... */ }

    public Builder addBaz(String value) { /* ... */ }
    public Builder addAllBaz(Iterable<String> values) { /* ... */ }
    public Builder clearBaz() { /* ... */ }
  }
}
```

Notice that methods of `Builder` such as `setBar`, `addBar`, and `addAllBaz` does not allow `null` parameters (they will throw `NullPointerException` if you do so). We should always use `clear**` methods, which is highly inconvenient.

With this plugin, the generated Java code will look like:

```java
public class Foo {
  /* ... */

  public static final class Builder {
    /* ... */

    public Builder setBar(String value) { /* ... */ }
    public Builder clearBar() { /* ... */ }
    public Builder setOrClearBar(String value) { /* ... */ }
    public <T> Builder mapOrClearBar(T value, Function<T, String> mapFunc) { /* ... */ }

    public Builder addBaz(String value) { /* ... */ }
    public Builder addAllBaz(Iterable<String> values) { /* ... */ }
    public Builder clearBaz() { /* ... */ }
    public Builder addAllOrClearBaz(Iterable<String> values) { /* ... */ }
    public Builder mapAllOrClearBaz(Iterable<?> values, Function<?, String> mapFunc) { /* ... */ }
  }
}
```

Newly added methods such as `setOrClearBar` and `addAllOrClearBaz` will accept `null` parameters, and will clear the field if the parameter is `null`.
