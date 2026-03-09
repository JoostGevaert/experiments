# 3D Standards & Web Visualisualization

3D web visualization experiments (USD, GLTF, 3D tiles, Three.js, etc.)

## USD

USD (Universal Scene Description) is a framework developed by Pixar for defining, composing, simulating, and collaborating on 3D data. It enables complex scene descriptions, consisting of geometry, shading, animation, lighting, and other elements, to be efficiently stored and shared across multiple teams and software. USD is highly scalable and suitable for workflows in VFX, animation, gaming, and other industries dealing with complex 3D scenes.

A USD file is a plain text file (or binary) with a .usd, .usda (ASCII), or .usdc (binary compressed) extension. Here's a simple example in the USD ASCII format (.usda):

```usda
(
    doc = "A simple USD scene"
)

def Sphere "mySphere" {
    float3 xformOp:translate = (0, 0, 0)
    uniform token[] xformOpOrder = ["xformOp:translate"]
    double radius = 1
}
```
[sphere.usda](./usd/sphere.usda)

This defines a scene containing a single sphere named mySphere positioned at the origin (0, 0, 0) with a radius of 1.


## glTF

glTF (GL Transmission Format) is a JSON-based file format designed for efficient transmission and loading of 3D models and scenes. Developed by the Khronos Group, it serves as a universal format for 3D models, making it easier for developers to use in applications, engines, and browsers. glTF is often referred to as the "JPEG of 3D" due to its optimized size and quick load times.

Key Features of glTF:

- Compactness: glTF files are designed to be lightweight and minimize the amount of data that needs to be transmitted.
- JSON or Binary: glTF files can be in JSON format (.gltf) or binary format (.glb), which combines the JSON and binary data into a single file for easier handling.
- PBR Materials: glTF supports physically based rendering (PBR), allowing for realistic materials and lighting.
- Interoperability: Works well across different platforms and devices.

### OpenGL

GL in glTF comes from OpenGL, which stands for "Open Graphics Library", which is a cross-language, cross-platform API for rendering 2D and 3D vector graphics. glTF was developed by the Khronos Group, the same organization that manages the OpenGL specification. The "GL" in glTF emphasizes its design focus on graphics applications and interoperability with OpenGL and similar graphics APIs.
