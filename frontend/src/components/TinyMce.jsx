import { Editor } from "@tinymce/tinymce-react";
import { useState } from "react";

function ProductCreate() {
  const [, setContent] = useState("");

  return (
    <Editor
      initialValue="<p>Nội dung mô tả...</p>"
      init={{
        height: 500,
        menubar: false,
        plugins: [
          "advlist autolink lists link image charmap preview anchor",
          "searchreplace visualblocks code fullscreen",
          "insertdatetime media table paste code help wordcount",
        ],
        toolbar:
          "undo redo | formatselect | bold italic backcolor | \
          alignleft aligncenter alignright alignjustify | \
          bullist numlist outdent indent | removeformat | help",
      }}
      onEditorChange={(newContent) => setContent(newContent)}
    />
  );
}

export default ProductCreate;
