self.addEventListener(
    "install",
    function(event){

        event.waitUntil(

            caches.open(
                "codequest-v1"
            ).then(function(cache){

                return cache.addAll([
                    "/",
                    "/static/style.css",
                    "/static/script.js"
                ]);
            })
        );
    }
);