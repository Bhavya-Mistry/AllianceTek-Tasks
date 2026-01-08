import onnxruntime as ort
import numpy as np
import cv2
import matplotlib.pyplot as plt

def load_model(model_path):
    """Load ONNX model"""
    session = ort.InferenceSession(model_path)
    return session

def preprocess_image(image_path):
    """Preprocess image for model input"""
    # Load image
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Resize to model input size
    image_resized = cv2.resize(image_rgb, (256, 256))
    
    # Normalize to [0, 1]
    image_normalized = image_resized.astype(np.float32) / 255.0
    
    # Convert to model input format (NCHW)
    input_tensor = np.transpose(image_normalized, (2, 0, 1))[np.newaxis, ...]
    
    return input_tensor, image_rgb

def run_inference(session, input_tensor):
    """Run inference on the model"""
    # Get input name
    input_name = session.get_inputs()[0].name
    
    # Run inference
    outputs = session.run(None, {input_name: input_tensor})
    
    # Apply sigmoid to get probabilities
    mask = 1.0 / (1.0 + np.exp(-outputs[0]))
    
    return mask.squeeze()

def visualize_results(original_image, mask, threshold=0.5):
    """Visualize the segmentation results"""
    # Create binary mask
    binary_mask = (mask > threshold).astype(np.uint8) * 255

    # Resize binary_mask to match original_image if needed
    if binary_mask.shape[:2] != original_image.shape[:2]:
        binary_mask_resized = cv2.resize(binary_mask, (original_image.shape[1], original_image.shape[0]), interpolation=cv2.INTER_NEAREST)
    else:
        binary_mask_resized = binary_mask

    # Create overlay
    overlay = original_image.copy()
    overlay[binary_mask_resized > 0] = [255, 0, 0]  # Red overlay
    
    # Plot results
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    
    axes[0].imshow(original_image)
    axes[0].set_title('Original Image')
    axes[0].axis('off')
    
    axes[1].imshow(mask, cmap='hot')
    axes[1].set_title('Segmentation Heatmap')
    axes[1].axis('off')
    
    axes[2].imshow(binary_mask_resized, cmap='gray')
    axes[2].set_title('Binary Mask')
    axes[2].axis('off')

    axes[3].imshow(overlay)
    axes[3].set_title('Overlay')
    axes[3].axis('off')
    
    plt.tight_layout()
    plt.show()

def main():
    """Main example function"""
    # Load model
    model_path = "ultimate_v2_breakthrough_accurate.onnx"
    session = load_model(model_path)
    
    # Process image
    image_path = "images\sample_board_full_screen.png"  # Replace with your image
    input_tensor, original_image = preprocess_image(image_path)
    
    # Run inference
    mask = run_inference(session, input_tensor)
    
    # Visualize results
    visualize_results(original_image, mask)
    
    print(f"✅ Chess board segmentation completed!")
    print(f"📊 Mask shape: {mask.shape}")
    print(f"📈 Mask range: {mask.min():.3f} - {mask.max():.3f}")

if __name__ == "__main__":
    main()