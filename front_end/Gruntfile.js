module.exports = function(grunt) {
    'use strict';

    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),

        react: {
            tmp: {
                files: [
                    {
                        expand: true,
                        cwd: 'web/src/js',
                        src: ['**/*.jsx'],
                        dest: 'web/src/js/tmp',
                        ext: '.js'
                    }
                ]
            }
        },

        jshint: {
            all: {
                options: {
                    '-W064': true,
                    '-W097': true,
                    'browser': true,
                    'devel': true,
                    globals: {
                        $: true,
                        module: true,
                        require: true
                    }
                },
                files: {
                    src: ['web/src/js/**/*.js']
                }
            }
        },

        clean: {
            tmp: ['web/src/js/tmp']
        },

        browserify: {
            options: {
                transform: [ require('grunt-react').browserify ]
            },
            app:    {
                files: {
                    'web/static/build/js/train-ensemble.js': ['web/src/js/TrainEnsemble.js'],
                    'web/static/build/js/data-manager.js': ['web/src/js/DataManager.js'],
                    'web/static/build/js/ensembles-list.js': ['web/src/js/EnsemblesList.js'],
                    'web/static/build/js/predict-dashboard.js': ['web/src/js/Predict.js']
                }
            }
        },

        watch: {
            browserify: {
                files: 'web/src/js/**/*.js*',
                tasks: ['browserify'],
                options: {livereload: true}
            }
        }
    });

    grunt.loadNpmTasks('grunt-react');
    grunt.loadNpmTasks('grunt-browserify');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-notify');
    grunt.loadNpmTasks('grunt-contrib-jshint');
    grunt.loadNpmTasks('grunt-contrib-clean');

    grunt.registerTask('default', ['browserify', 'watch']);
    grunt.registerTask('lint', ['react:tmp', 'jshint:all', 'clean:tmp']);
    grunt.registerTask('build', ['browserify']);
};
