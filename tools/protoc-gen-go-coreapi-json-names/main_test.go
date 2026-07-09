package main

import (
	"strings"
	"testing"

	"github.com/golang/protobuf/proto"
	plugin "github.com/golang/protobuf/protoc-gen-go/plugin"
	"google.golang.org/protobuf/types/descriptorpb"
)

func TestProcess_generatesCoreAPIJSONNameLookup(t *testing.T) {
	// Given
	req := &plugin.CodeGeneratorRequest{
		FileToGenerate: []string{"coreapi/service/group.proto"},
		ProtoFile: []*descriptorpb.FileDescriptorProto{
			{
				Name:    proto.String("coreapi/service/group.proto"),
				Package: proto.String("coreapi.service"),
				Options: &descriptorpb.FileOptions{
					GoPackage: proto.String("github.com/channel-io/ch-proto-public/coreapi/go/service"),
				},
				MessageType: []*descriptorpb.DescriptorProto{
					{
						Name: proto.String("PatchGroupBody"),
						Field: []*descriptorpb.FieldDescriptorProto{
							{
								Name:     proto.String("description"),
								JsonName: proto.String("description"),
								Type:     descriptorpb.FieldDescriptorProto_TYPE_STRING.Enum(),
							},
						},
					},
					{
						Name: proto.String("PatchGroupRequest"),
						Field: []*descriptorpb.FieldDescriptorProto{
							{
								Name: proto.String("user_chat_id"),
								Type: descriptorpb.FieldDescriptorProto_TYPE_STRING.Enum(),
							},
							{
								Name:     proto.String("bot_name"),
								JsonName: proto.String("botName"),
								Type:     descriptorpb.FieldDescriptorProto_TYPE_STRING.Enum(),
							},
							{
								Name:     proto.String("body"),
								JsonName: proto.String("body"),
								Type:     descriptorpb.FieldDescriptorProto_TYPE_MESSAGE.Enum(),
								TypeName: proto.String(".coreapi.service.PatchGroupBody"),
							},
						},
					},
				},
			},
		},
	}
	resp := &plugin.CodeGeneratorResponse{}

	// When
	err := process(req, resp)

	// Then
	if err != nil {
		t.Fatalf("process() error = %v", err)
	}
	if got, want := len(resp.File), 1; got != want {
		t.Fatalf("len(resp.File) = %d, want %d", got, want)
	}
	if got, want := resp.File[0].GetName(), "coreapi/go/jsonnames/coreapi_json_names.go"; got != want {
		t.Fatalf("resp.File[0].Name = %q, want %q", got, want)
	}

	content := resp.File[0].GetContent()
	for _, want := range []string{
		"func FieldPath(messageFullName, protoPath string) (string, bool)",
		`"coreapi.service.PatchGroupRequest": {`,
		`"user_chat_id":`,
		`{jsonName: "userChatId"}`,
		`"bot_name":`,
		`{jsonName: "botName"}`,
		`"body":`,
		`{jsonName: "body", messageFullName: "coreapi.service.PatchGroupBody"}`,
	} {
		if !strings.Contains(content, want) {
			t.Fatalf("generated content does not contain %q:\n%s", want, content)
		}
	}
}
