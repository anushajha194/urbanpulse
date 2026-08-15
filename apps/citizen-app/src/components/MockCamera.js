import React, { useState } from 'react';
import { View, Text, Image, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

// Local sample photos — actual civic issue images
const potholeImg = require('../../assets/pothole.png');
const streetlightImg = require('../../assets/streetlight.png');
const waterloggingImg = require('../../assets/waterlogging.png');

export default function MockCamera({ imageUri, onSelectPhoto }) {
  const [cameraPermissionDenied, setCameraPermissionDenied] = useState(false);

  const samplePhotos = [
    { source: potholeImg, label: 'Pothole' },
    { source: streetlightImg, label: 'Street Light' },
    { source: waterloggingImg, label: 'Waterlogging' },
  ];

  // ─── Open device camera ───
  const handleOpenCamera = async () => {
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        setCameraPermissionDenied(true);
        // Fallback: open gallery instead
        handleOpenGallery();
        return;
      }
      setCameraPermissionDenied(false);

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        quality: 0.8,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        onSelectPhoto(result.assets[0].uri);
      }
    } catch (err) {
      console.warn('Camera not available, opening gallery instead:', err);
      handleOpenGallery();
    }
  };

  // ─── Open photo gallery ───
  const handleOpenGallery = async () => {
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') {
        // If permissions denied everywhere, fall back to sample photos
        handleSelectSample(samplePhotos[0]);
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        quality: 0.8,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        onSelectPhoto(result.assets[0].uri);
      }
    } catch (err) {
      console.warn('Gallery not available:', err);
    }
  };

  // ─── Select a sample photo ───
  const handleSelectSample = (photo) => {
    // For local images, resolve the asset and use a data URI or asset URI
    const asset = Image.resolveAssetSource(photo.source);
    if (asset && asset.uri) {
      onSelectPhoto(asset.uri);
    }
  };

  return (
    <View style={styles.container}>
      {imageUri ? (
        /* ─── Photo Preview State ─── */
        <View style={styles.previewContainer}>
          <Image source={{ uri: imageUri }} style={styles.previewImage} />
          {/* Success overlay badge */}
          <View style={styles.successBadge}>
            <Text style={styles.successIcon}>✓</Text>
            <Text style={styles.successText}>Photo captured</Text>
          </View>
          {/* Action buttons row */}
          <View style={styles.previewActions}>
            <TouchableOpacity
              style={styles.changeBtn}
              onClick={handleOpenCamera}
              onPress={handleOpenCamera}
              accessibilityLabel="Retake photo with camera"
              accessibilityRole="button"
            >
              <Text style={styles.changeBtnIcon}>📷</Text>
              <Text style={styles.changeBtnText}>Retake</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.changeBtn}
              onClick={handleOpenGallery}
              onPress={handleOpenGallery}
              accessibilityLabel="Choose different photo from gallery"
              accessibilityRole="button"
            >
              <Text style={styles.changeBtnIcon}>🖼️</Text>
              <Text style={styles.changeBtnText}>Gallery</Text>
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        /* ─── Empty / Capture State ─── */
        <View style={styles.captureContainer}>
          {/* Camera + Gallery buttons */}
          <View style={styles.captureButtonsRow}>
            <TouchableOpacity
              style={styles.captureMainBtn}
              onClick={handleOpenCamera}
              onPress={handleOpenCamera}
              accessibilityLabel="Open camera to take a photo of a civic issue"
              accessibilityRole="button"
            >
              <View style={styles.captureIconOuter}>
                <View style={styles.captureIconInner}>
                  <Text style={styles.captureIconSymbol}>📷</Text>
                </View>
              </View>
              <Text style={styles.captureBtnTitle}>Take Photo</Text>
              <Text style={styles.captureBtnSubtitle}>Use your camera</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.captureSecondaryBtn}
              onClick={handleOpenGallery}
              onPress={handleOpenGallery}
              accessibilityLabel="Choose a photo from your gallery"
              accessibilityRole="button"
            >
              <View style={styles.galleryIconOuter}>
                <Text style={styles.galleryIconSymbol}>🖼️</Text>
              </View>
              <Text style={styles.captureBtnTitle}>Gallery</Text>
              <Text style={styles.captureBtnSubtitle}>Choose existing</Text>
            </TouchableOpacity>
          </View>

          {/* Description */}
          <View style={styles.captureDescRow}>
            <Text style={styles.captureDesc}>
              Capture potholes, waterlogging, broken streetlights, or damaged infrastructure
            </Text>
          </View>

          {/* Sample photo quick-picks */}
          <View style={styles.samplesSection}>
            <Text style={styles.samplesLabel}>Or choose an example issue:</Text>
            <View style={styles.samplesRow}>
              {samplePhotos.map((photo, idx) => (
                <TouchableOpacity
                  key={idx}
                  style={styles.sampleThumb}
                  onClick={() => handleSelectSample(photo)}
                  onPress={() => handleSelectSample(photo)}
                  accessibilityLabel={`Select sample photo: ${photo.label}`}
                  accessibilityRole="button"
                >
                  <Image source={photo.source} style={styles.sampleImage} />
                  <Text style={styles.sampleLabel}>{photo.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    marginBottom: 20,
    borderRadius: 16,
    overflow: 'hidden',
  },

  /* ─── Capture State ─── */
  captureContainer: {
    backgroundColor: '#111827',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(88, 166, 255, 0.15)',
    overflow: 'hidden',
  },
  captureButtonsRow: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  captureMainBtn: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 24,
    backgroundColor: 'rgba(88, 166, 255, 0.06)',
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: 'rgba(88, 166, 255, 0.2)',
    borderStyle: 'dashed',
  },
  captureSecondaryBtn: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 24,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  captureIconOuter: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(88, 166, 255, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
    borderWidth: 2,
    borderColor: 'rgba(88, 166, 255, 0.2)',
  },
  captureIconInner: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(88, 166, 255, 0.15)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  captureIconSymbol: {
    fontSize: 20,
  },
  galleryIconOuter: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  galleryIconSymbol: {
    fontSize: 22,
  },
  captureBtnTitle: {
    color: '#e6edf3',
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 2,
  },
  captureBtnSubtitle: {
    color: '#8b949e',
    fontSize: 11,
  },
  captureDescRow: {
    paddingHorizontal: 20,
    paddingBottom: 14,
  },
  captureDesc: {
    color: '#484f58',
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
  },

  /* ─── Sample Photos ─── */
  samplesSection: {
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.05)',
    backgroundColor: 'rgba(0, 0, 0, 0.15)',
  },
  samplesLabel: {
    color: '#8b949e',
    fontSize: 11,
    fontWeight: '600',
    marginBottom: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  samplesRow: {
    flexDirection: 'row',
    gap: 10,
    justifyContent: 'center',
  },
  sampleThumb: {
    flex: 1,
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 10,
    paddingBottom: 8,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.05)',
  },
  sampleImage: {
    width: '100%',
    height: 72,
    borderTopLeftRadius: 9,
    borderTopRightRadius: 9,
    resizeMode: 'cover',
  },
  sampleLabel: {
    color: '#8b949e',
    fontSize: 10,
    fontWeight: '600',
  },

  /* ─── Preview State ─── */
  previewContainer: {
    width: '100%',
    height: 260,
    borderRadius: 16,
    overflow: 'hidden',
    position: 'relative',
  },
  previewImage: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  successBadge: {
    position: 'absolute',
    top: 12,
    left: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(63, 185, 80, 0.9)',
    paddingVertical: 5,
    paddingHorizontal: 12,
    borderRadius: 20,
  },
  successIcon: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  successText: {
    color: '#ffffff',
    fontSize: 11,
    fontWeight: '700',
  },
  previewActions: {
    position: 'absolute',
    bottom: 14,
    right: 14,
    flexDirection: 'row',
    gap: 8,
  },
  changeBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(13, 17, 23, 0.9)',
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(88, 166, 255, 0.3)',
  },
  changeBtnIcon: {
    fontSize: 13,
  },
  changeBtnText: {
    color: '#58a6ff',
    fontSize: 12,
    fontWeight: '700',
  },
});
