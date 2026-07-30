# protoc-gen-java-canonical-enum-namings

This is a protoc plugin that generates Java code with canonical enum namings. The generated Java code contains utility methods that supports conversions between Java enums and protobuf enums, each following their naming conventions.

For example, given the following protobuf definition:

```proto
enum Foo {
  FOO_UNSPECIFIED = 0;
  FOO_BAR = 1;
  FOO_BAZ = 2;
}
```

The generated Java code will look like:

```java
enum Foo {
  FOO_UNSPECIFIED(0),
  FOO_BAR(1),
  FOO_BAZ(2);

  private final int value;

  /* ... */

  public static Foo forString(String name) {
    switch (name) {
      case "bar": return FOO_BAR;
      case "baz": return FOO_BAZ;
      default: return FOO_UNSPECIFIED;
    }
  }

  public final String getString() {
    switch (this) {
      case FOO_BAR: return "bar";
      case FOO_BAZ: return "baz";
      default: return null;
    }
  }
}
```
