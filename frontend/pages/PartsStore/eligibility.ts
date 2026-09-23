import { partsStoreCatalogue, type StoreProduct } from '../../data/partsStoreCatalogue.ts'
import type { CartItem } from '../../types/api.ts'

export type CartItemClassification =
  | 'VERIFIED'
  | 'UNVERIFIED_SOURCE_MISMATCH'
  | 'UNVERIFIED_INTERNAL_REF'
  | 'AMBIGUOUS'
  | 'PRODUCT_FAMILY'
  | 'ATTACHMENT_FAMILY'
  | 'UNKNOWN'

export interface ItemEligibilityResult {
  classification: CartItemClassification
  isEligible: boolean
  partNumberDisplay: string
  isPartNumberUnverified: boolean
  badgeLabel: string
  badgeClass: string
  buttonLabel: string
  buttonTitle: string
  actionType: 'CHECKOUT' | 'IDENTIFY_SERIAL' | 'REQUEST_VERIFICATION' | 'REQUEST_IDENTIFICATION'
  note: string | null
}

export function getProductForCartItem(item: CartItem): StoreProduct | undefined {
  return partsStoreCatalogue.find((p) => p.id === item.id)
}

/**
 * Authoritative Central Data-Truth Eligibility Service (Phase 11)
 *
 * An item is eligible for active checkout ONLY if:
 * 1. It carries a genuine, non-empty OEM part number.
 * 2. It has no provenance warning (not SOURCE_MISMATCH_UNVERIFIED, not INTERNALLY_GENERATED_UNVERIFIED).
 * 3. It is not an ambiguous multi-SKU assembly (such as hydraulic-cylinder or fuel-injection-pump).
 *
 * All non-eligible items present active, guided paths (no dead disabled buttons).
 */
export function classifyCartItem(item: CartItem): ItemEligibilityResult {
  const product = getProductForCartItem(item)
  const isAmbiguous =
    (item.id === 'hydraulic-cylinder' || item.id === 'fuel-injection-pump') &&
    (!item.partNumber || item.partNumber.trim() === '' || item.partNumber === '—' || item.partNumber.toLowerCase().includes('multiple'))
  const isSourceMismatch = product?.provenanceStatus === 'SOURCE_MISMATCH_UNVERIFIED'
  const isInternalRef = product?.provenanceStatus === 'INTERNALLY_GENERATED_UNVERIFIED'
  const isAttachment = product?.category?.startsWith('Attachments')
  const isProductFamily = product?.category?.includes('Lubricant') || product?.category?.includes('Reman')

  // 1. Ambiguous multi-SKU assemblies
  if (isAmbiguous) {
    return {
      classification: 'AMBIGUOUS',
      isEligible: false,
      partNumberDisplay: 'Multiple OEM matches',
      isPartNumberUnverified: false,
      badgeLabel: '⚠ Multiple OEM assemblies found',
      badgeClass: 'ps-cart-badge--ambiguous',
      buttonLabel: 'Identify by machine/serial →',
      buttonTitle: 'Identify exact OEM assembly with machine model and serial number',
      actionType: 'IDENTIFY_SERIAL',
      note:
        item.id === 'hydraulic-cylinder'
          ? 'Hitachi utilizes separate Boom (4410244), Arm (4385638), and Bucket (4385637) cylinder assemblies. Exact OEM identification requires machine model and equipment serial number.'
          : 'Fuel injection pump is specific to the machine engine block (e.g. Isuzu 4HK1/6HK1). Engine serial number required.',
    }
  }

  // 2. Source Mismatch Unverified (e.g., PT-054..PT-060)
  if (isSourceMismatch) {
    return {
      classification: 'UNVERIFIED_SOURCE_MISMATCH',
      isEligible: false,
      partNumberDisplay: item.partNumber || '—',
      isPartNumberUnverified: true,
      badgeLabel: '⚠ Part verification required (Source mismatch)',
      badgeClass: 'ps-cart-badge--warning',
      buttonLabel: 'Request verification →',
      buttonTitle: 'Request parts specialist verification before placing an order',
      actionType: 'REQUEST_VERIFICATION',
      note: 'Attributed to service channel reference (SRC-042); unverified against official HCME parts catalog. Requires specialist verification before checkout.',
    }
  }

  // 3. Internally Generated Unverified (e.g., PT-044..PT-048)
  if (isInternalRef) {
    return {
      classification: 'UNVERIFIED_INTERNAL_REF',
      isEligible: false,
      partNumberDisplay: item.partNumber || '—',
      isPartNumberUnverified: true,
      badgeLabel: '⚠ Verification required (Internal reference)',
      badgeClass: 'ps-cart-badge--warning',
      buttonLabel: 'Request verification →',
      buttonTitle: 'Request parts specialist technical verification before checkout',
      actionType: 'REQUEST_VERIFICATION',
      note: 'Internal specification reference (SRC-048). Technical verification required before checkout.',
    }
  }

  // 4. Real verified parts with non-empty part number
  if (
    item.partNumber &&
    item.partNumber.trim() !== '' &&
    item.partNumber !== '—' &&
    !item.partNumber.toUpperCase().startsWith('NOT ')
  ) {
    return {
      classification: 'VERIFIED',
      isEligible: true,
      partNumberDisplay: item.partNumber,
      isPartNumberUnverified: false,
      badgeLabel: '✓ Ready for fulfilment',
      badgeClass: 'ps-cart-badge--ready',
      buttonLabel: 'Check stock & fulfil →',
      buttonTitle: 'Launch guided European fulfilment checkout',
      actionType: 'CHECKOUT',
      note: null,
    }
  }

  // 5. Attachment Family
  if (isAttachment) {
    return {
      classification: 'ATTACHMENT_FAMILY',
      isEligible: false,
      partNumberDisplay: 'Not identified',
      isPartNumberUnverified: false,
      badgeLabel: '⚠ Part identification required',
      badgeClass: 'ps-cart-badge--warning',
      buttonLabel: 'Request identification →',
      buttonTitle: 'Submit an enquiry to identify the exact OEM attachment tool for your machine',
      actionType: 'REQUEST_IDENTIFICATION',
      note: 'Fitment is determined by machine pin/bracket geometry. Submit an enquiry with your machine model.',
    }
  }

  // 6. Product Line / Family / Oils / Fluids / Unknown
  return {
    classification: isProductFamily ? 'PRODUCT_FAMILY' : 'UNKNOWN',
    isEligible: false,
    partNumberDisplay: 'Not identified',
    isPartNumberUnverified: false,
    badgeLabel: '⚠ Part identification required',
    badgeClass: 'ps-cart-badge--warning',
    buttonLabel: 'Request identification →',
    buttonTitle: 'Submit an enquiry to identify the exact OEM part number for your machine',
    actionType: 'REQUEST_IDENTIFICATION',
    note: 'Published OEM part number required to check warehouse stock. Submit an enquiry with your machine model and serial number.',
  }
}

export function isFulfilmentEligible(item: CartItem): boolean {
  return classifyCartItem(item).isEligible
}
