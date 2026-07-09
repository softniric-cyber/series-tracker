export default function Footer() {
  return (
    <footer className="border-t border-neutral-200 py-6 text-center text-xs text-neutral-500 dark:border-neutral-800">
      <p className="mx-auto max-w-3xl px-4">
        Este producto usa la API de TMDB pero no está avalado ni certificado por TMDB. Datos y
        pósters proporcionados por{' '}
        <a
          href="https://www.themoviedb.org/"
          target="_blank"
          rel="noreferrer"
          className="font-medium text-brand-600 hover:underline"
        >
          The Movie Database (TMDB)
        </a>
        .
      </p>
    </footer>
  )
}
