import { describe, it, expect, vi } from 'vitest'

// Mock the Cloudinary SDK before importing mediaConfig
vi.mock('@cloudinary/url-gen', () => {
  const mockToURL = vi.fn().mockReturnValue('https://res.cloudinary.com/dgyptiexk/image/upload/test.jpg')
  const mockAsset = { resize: vi.fn().mockReturnThis(), format: vi.fn().mockReturnThis(), toURL: mockToURL }
  // Must use function (not arrow) so it works as a `new` constructor
  function MockCloudinary(this: any) {
    this.image = vi.fn(() => mockAsset)
    this.video = vi.fn(() => mockAsset)
  }
  return { Cloudinary: MockCloudinary }
})

vi.mock('@cloudinary/url-gen/actions/resize', () => ({
  fill: vi.fn(() => ({
    width: vi.fn().mockReturnThis(),
    height: vi.fn().mockReturnThis(),
    gravity: vi.fn().mockReturnThis(),
  })),
}))

vi.mock('@cloudinary/url-gen/qualifiers/gravity', () => ({
  autoGravity: vi.fn(),
}))

describe('mediaConfig', () => {
  describe('Case 1: Cloudinary public_id (no https:// prefix)', () => {
    it('returns a Cloudinary URL as primary when image_url is a public_id', async () => {
      // Set cloud name env var so Cloudinary client initialises
      vi.stubEnv('VITE_CLOUDINARY_CLOUD_NAME', 'dgyptiexk')
      vi.resetModules()

      const { getMediaUrls } = await import('./mediaConfig')

      const publicId = 'hackcanada/tiktok/7611759033564810514'
      const s3Url = 'https://hackcanada.s3.us-east-2.amazonaws.com/media/tiktok/7611759033564810514.mp4'

      const { primary, fallback } = getMediaUrls(publicId, s3Url)

      // Primary must be a Cloudinary delivery URL (contains cloudinary.com)
      expect(primary).toContain('cloudinary.com')
      // Fallback must be the s3 URL
      expect(fallback).toBe(s3Url)
    })

    it('falls back to s3_url when Cloudinary is not configured', async () => {
      vi.stubEnv('VITE_CLOUDINARY_CLOUD_NAME', '')
      vi.resetModules()

      const { getMediaUrls } = await import('./mediaConfig')

      const publicId = 'hackcanada/tiktok/7611759033564810514'
      const s3Url = 'https://hackcanada.s3.us-east-2.amazonaws.com/media/tiktok/7611759033564810514.mp4'

      const { primary, fallback } = getMediaUrls(publicId, s3Url)

      // Without Cloudinary configured, primary falls back to placeholder
      expect(primary).toBe('/placeholder-event.svg')
      expect(fallback).toBe(s3Url)
    })
  })

  describe('Case 2: Direct https:// URL (S3 or CDN)', () => {
    it('returns the URL directly as primary with no fallback', async () => {
      vi.resetModules()
      const { getMediaUrls } = await import('./mediaConfig')

      const s3Direct = 'https://hackcanada.s3.us-east-2.amazonaws.com/media/x/abc123.mp4'

      const { primary, fallback } = getMediaUrls(s3Direct, null)

      expect(primary).toBe(s3Direct)
      expect(fallback).toBeNull()
    })

    it('works with any https:// URL regardless of domain', async () => {
      vi.resetModules()
      const { getMediaUrls } = await import('./mediaConfig')

      const cdnUrl = 'https://pbs.twimg.com/ext_tw_video/123/pu/vid/video.mp4'

      const { primary, fallback } = getMediaUrls(cdnUrl, undefined)

      expect(primary).toBe(cdnUrl)
      expect(fallback).toBeNull()
    })
  })

  describe('Case 3: No image (null / undefined)', () => {
    it('returns placeholder SVG when image_url is null', async () => {
      vi.resetModules()
      const { getMediaUrls } = await import('./mediaConfig')

      const { primary, fallback } = getMediaUrls(null, null)

      expect(primary).toBe('/placeholder-event.svg')
      expect(fallback).toBeNull()
    })

    it('returns placeholder SVG when image_url is undefined', async () => {
      vi.resetModules()
      const { getMediaUrls } = await import('./mediaConfig')

      const { primary, fallback } = getMediaUrls(undefined, undefined)

      expect(primary).toBe('/placeholder-event.svg')
      expect(fallback).toBeNull()
    })

    it('returns placeholder SVG when image_url is empty string', async () => {
      vi.resetModules()
      const { getMediaUrls } = await import('./mediaConfig')

      const { primary, fallback } = getMediaUrls('', null)

      expect(primary).toBe('/placeholder-event.svg')
      expect(fallback).toBeNull()
    })
  })

  describe('getEventImageUrl convenience wrapper', () => {
    it('returns just the primary string', async () => {
      vi.resetModules()
      const { getEventImageUrl } = await import('./mediaConfig')

      const url = getEventImageUrl('https://example.com/image.jpg')
      expect(url).toBe('https://example.com/image.jpg')
    })
  })
})
