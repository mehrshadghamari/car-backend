window.FA = {
  dealTag: {
    best: 'بهترین',
    good: 'خوب',
    normal: 'عادی',
    fair: 'منصفانه',
  },
  status: {
    active: 'فعال',
    inactive: 'غیرفعال',
    pending: 'در صف بررسی',
    queued: 'در انتظار تأیید',
    monitoring: 'در حال پایش',
    failed: 'خطا در بررسی',
  },
  pricing: {
    khodro45: 'خودرو۴۵',
    hamrah_mechanic: 'همراه مکانیک',
  },
  city: {
    tehran: 'تهران',
    mashhad: 'مشهد',
    isfahan: 'اصفهان',
    shiraz: 'شیراز',
  },
  errors: {
    phoneRequired: 'شماره موبایل را وارد کنید',
    modelRequired: 'مدل خودرو را انتخاب کنید',
    requestFailed: 'خطا در ارتباط با سرور',
    invalidOtp: 'کد تأیید نامعتبر یا منقضی شده است',
  },
};

function faCity(slug) {
  if (!slug) return '—';
  return window.FA.city[slug.toLowerCase()] || slug;
}

function faPricing(slug) {
  if (!slug) return '—';
  return window.FA.pricing[slug] || slug;
}

function fmtFaNum(n) {
  if (n == null || n === '') return '—';
  return Number(n).toLocaleString('fa-IR');
}

function fmtFaDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('fa-IR', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

function faDealTag(tag) {
  return window.FA.dealTag[tag] || tag || '—';
}
