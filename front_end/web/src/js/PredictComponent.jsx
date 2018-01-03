/** @jsx React.DOM */
/* global React */
/* global _ */

"use strict";
var Utils = require('./Utils');


var RadioButtonReact = React.createClass({
    render: function() {
        return (
            <label className={this.props.disabled}>
                <span className="custom-radio">
                    <input type="radio" name={this.props.name}
                                        checked={this.props.checked}
                                        onChange={this.props.handleChange || function() {}} />
                    <i></i>
                </span>
                {this.props.text}
                {this.props.note ? <small>{this.props.note}</small> : ''}
            </label>
        );
    }
});

var PredictFirstPanelReact = React.createClass({
    getInitialState: function() {
        return {checked: false};
    },

    handleChange: function(task, e) {
        this.props.handleChange(task, e);
    },

    redirectOnUpload: function(e) {
        e.preventDefault();
        window.location.href = '/dashboard/';
    },

    render: function() {
        var selectedTask = this.props.selectedTask;
        var component = (
            <ul className="radios-list">
                <li>
                    <RadioButtonReact name="step1" checked={selectedTask === "input_data"}
                                      text="Enter data directly into my browser"
                                      handleChange={this.handleChange.bind(this, "input_data")} />
                </li>
                <li>
                    <RadioButtonReact name="step1" checked={selectedTask === "dataset"}
                                      text="Use dataset I've already uploaded"
                                      handleChange={this.handleChange.bind(this, "dataset")} />
                </li>
                <li>
                    <RadioButtonReact name="step1" checked={selectedTask === "results"}
                                      text="Retrieve previous predictions I've made"
                                      handleChange={this.handleChange.bind(this, "results")} />
                </li>
                <li>
                    <a href="#" className="dataset-upload" onClick={this.redirectOnUpload}>
                        <i className="icon icon-white icon-arrow-up"></i>
                        {"I have a new dataset I'd like to upload now"}
                    </a>
                </li>
            </ul>
        );

        return (
            <div className="panel panel-blue">
                <PredictWizardHead title="How would you like to use your model?" />
                <PredictWizardBody component={component} />
            </div>
        );
    }
});

var PredictSecondPanelReact = React.createClass({
    getInitialState: function() {
        return {checked: false};
    },

    handleChange: function(number, e) {
        if (e.target.checked) {
            this.setState({checked: number});
        }
    },

    render: function() {
        var component = (
            <ul className="radios-list">
                <li>
                    <RadioButtonReact name="step2" checked="true"
                                      text="Output values"
                                      note="Returns softmax of classes or single column of regression/linear/sigmoid outputs"
                                      />
                </li>
                <li>
                    <RadioButtonReact name="step2" disabled="disabled"
                                      text="Hidden unit activations"
                                      note="Returns the hidden unit activations of each sample"
                                      />
                </li>
            </ul>
        );

        return (
            <div className="panel panel-blue">
                <PredictWizardHead title="I'd like to retrieve:" />
                <PredictWizardBody component={component} />
            </div>
        );
    }
});

var PredictWizardHead = React.createClass({
    render: function() {
        return (
            <div className="panel-heading">
                <h2>{this.props.title}</h2>
            </div>
        );
    }
});

var PredictWizardBody = React.createClass({
    render: function() {
        return (
            <div className="panel-body">
                {this.props.component}
            </div>
        );
    }
});

var ResultTabsReact = React.createClass({
    getInitialState: function() {
        return {selectedTab: 'input_data'};
    },

    handleTabSelect: function(tab) {
        this.setState({selectedTab: tab});
    },

    render: function() {
        var body = null;
        if (!this.props.isLoaded) {
            return <div className="ajax-loader"></div>;
        }
        if (this.state.selectedTab === 'input_data') {
            body = <InputDataResultsTab ensemble={this.props.ensemble} />;
        } else {
            body = <DatasetResultsTab ensemble={this.props.ensemble} />;
        }
        return (
            <div>
                <ul className="tabs">
                    <li className={(this.state.selectedTab === 'input_data') ? "active" : ""} onClick={this.handleTabSelect.bind(this, 'input_data')}><i className="icon icon-white icon-tasks"></i> Input Data</li>
                    <li className={(this.state.selectedTab === 'datasets') ? "active" : ""} onClick={this.handleTabSelect.bind(this, 'datasets')}><i className="icon icon-white icon-download"></i> Datasets</li>
                </ul>
                <div className="tabs-pane">
                    {body}
                </div>
            </div>
        );
    }
});

var PredictWizardReact = React.createClass({
    getInitialState: function() {
        return {
            selectedTask: undefined,
            selectedOutput: 'output_values'
        };
    },

    handleTaskChange: function(task, e) {
        if (e.target.checked) {
            this.setState({selectedTask: task});
        }
    },

    render: function() {
        var body = null, secondPanel = null, tabs = null;
        if (this.state.selectedTask && this.state.selectedOutput) {
            if (this.state.selectedTask === 'results') {
                this.props.ensemble.loadPreviousPredictions();
                tabs = <ResultTabsReact ensemble={this.props.ensemble} isLoaded={this.props.ensemble.get('previousDatasetsIsLoaded')}/>;
            } else {
                tabs = <PredictTabsReact ensemble={this.props.ensemble} selectedTask={this.state.selectedTask}/>;
            }
            body = (
                <div className="row">
                    <div className="span3">
                        <PredictModelsReact ensemble={this.props.ensemble}/>
                    </div>
                    <div className="span9">
                        {tabs}
                    </div>
                </div>
            );
        }
        if (this.state.selectedTask) {
            secondPanel = <PredictSecondPanelReact />;
        }
        return (
            <div>
                <div className="wizard wizard-predict">
                    <PredictFirstPanelReact handleChange={this.handleTaskChange} selectedTask={this.state.selectedTask}/>
                    {secondPanel}
                </div>
                {body}
            </div>
        );
    }
});

var PredictEnsembleInfoReact = React.createClass({
    render: function() {
        var testAvg, trainAvg, modelIds, stat, models = this.props.models;
        modelIds = models.map(function(model) {
            return model.id;
        }).join(', ');
        trainAvg = models.map(function(model) {
            stat = model.get('selectedIter') || model.stats.last();
            return stat.get('train_accuracy');
        });
        trainAvg = Utils.sum(trainAvg) * 100 / models.length;
        testAvg = models.map(function(model) {
            stat = model.get('selectedIter') || model.stats.last();
            return stat.get('test_accuracy');
        });
        testAvg = Utils.sum(testAvg) * 100 / models.length;
        return (
            <div className="predict-ensemble">
                <h4>Ensemble #{this.props.ensemble.id} Information</h4>
                <ul className="dm-file-meta">
                    <li><strong>Models:</strong> {modelIds}</li>
                    <li><strong>Average Training / Testing:</strong> {trainAvg.toFixed(4)}% / {testAvg.toFixed(4)}%</li>
                </ul>
            </div>
        );
    }
});

var PredictInputData = React.createClass({
    getInitialState: function() {
        return {inputData: ''};
    },

    handleChangeInputData: function(e) {
        this.setState({inputData: e.target.value});
    },

    predict: function() {
        var ensemble = this.props.ensemble,
            props = this.props,
            self = this,
            iterations = ensemble.getIterationsForPredict();
        this.setState({ajaxPredictProcessing: true});
        $.ajax({
            url: '/api/predict/',
            type: 'POST',
            data: JSON.stringify({iterations: iterations, input_data: this.state.inputData}, null, 2),
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            ensemble.predicts.add(data);
            console.log('success');
            self.setState({ajaxPredictProcessing: false});
            props.handlePredict();
        }).fail(function (xhr) {
            self.setState({ajaxPredictProcessing: false});
            console.log('fail');
        });
    },

    render: function() {
        var label;
        if (this.props.ensemble.get('data_type') === 'TIMESERIES') {
            label = "Enter data in Time Series format:";
        } else {
            label = "Enter data in CSV-like format:";
        }
        if (this.state.ajaxPredictProcessing) {
            return <div className="ajax-loader"></div>;
        }
        return (
            <div>
                <div>
                    <label>
                        <i className="icon icon-white icon-file"></i>
                        <strong>{label}</strong>
                    </label>
                    <textarea className="dark" onChange={this.handleChangeInputData} value={this.state.inputData}></textarea>
                </div>
                <button className="btn btn-info" onClick={this.predict}>
                    <i className="icon icon-white icon-play"></i> Go Predict
                </button>
            </div>
        );
    }
});

var PredictDataset = React.createClass({
    getInitialState: function() {
        return {selectedDataset: this.props.ensemble.get('test_dataset')};
    },

    predict: function() {
        var ensemble = this.props.ensemble,
            props = this.props,
            self = this,
            iterations = ensemble.getIterationsForPredict();
        this.setState({ajaxPredictProcessing: true});
        $.ajax({
            url: '/api/predict/',
            type: 'POST',
            data: JSON.stringify({iterations: iterations, dataset: this.state.selectedDataset}, null, 2),
            dataType: 'json',
            contentType: 'application/json'
        }).done(function (data) {
            console.log('success');
            ensemble.predicts.add(data);
            self.setState({ajaxPredictProcessing: false});
            props.handlePredict();
        }).fail(function (xhr) {
            self.setState({ajaxPredictProcessing: false});
            console.log('fail');
        });
    },

    handleDatasetSelect: function(e) {
        this.setState({selectedDataset: e.target.value});
    },

    render: function() {
        var options = null, datasets = this.props.ensemble.get('possibleDatasets'), models;
        if (this.state.ajaxPredictProcessing) {
            return <div className="ajax-loader"></div>;
        }
        options = datasets.map(function(dataset) {
            return <option key={dataset.id} value={dataset.id}>{dataset.name}</option>;
        });
        return (
            <div>
                <div>
                    <label className="dib">
                        <i className="icon icon-white icon-file"></i>
                        <strong>Select dataset for prediction:</strong>
                    </label>
                    <select value={this.state.selectedDataset} onChange={this.handleDatasetSelect}>
                        {options}
                    </select>
                </div>
                <button className="btn btn-info" onClick={this.predict}>
                    <i className="icon icon-white icon-play"></i> Go Predict
                </button>
            </div>
        );
    }
});

var Dropbox = React.createClass({
    handleOnDragEnter: function(e) {
        e.stopPropagation();
        e.preventDefault();
    },

    handleOnDragOver: function(e) {
        e.stopPropagation();
        e.preventDefault();
    },

    imgOnLoad: function(file) {
        return function(e) {
            file.srcLink = e.target.result;
            this.props.parentForceUpdate();
        }.bind(this);
    },

    handleDrop: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var dt = e.dataTransfer,
            props = this.props,
            files = dt.files,
            fileSet = props.ensemble.get('fileSet'),
            file,
            imageType = /image.*/,
            reader;
        for (var i = 0; i < files.length; i++) {
            file = files[i];
            if (!file.type.match(imageType)) {
                continue;
            }
            reader = new FileReader();
            reader.onload = this.imgOnLoad(file);
            reader.readAsDataURL(file);
            fileSet.push(file);
        }
        props.ensemble.set('fileSet', fileSet);
    },

    render: function() {
        var images = this.props.ensemble.get('fileSet').filter(function(file) {
            return file.srcLink;
        }).map(function(file, i) {
            return (
                <div key={i} className="thumbnails-item">
                    <span className="thumbnails-img"><img src={file.srcLink} /></span>
                </div>
            );
        });

        return (
            <div className="images-upload">
                <div
                    onDragEnter={this.handleOnDragEnter}
                    onDragOver={this.handleOnDragOver}
                    onDrop={this.handleDrop}
                    className="dropbox">
                        Drag and drop images here.
                </div>
                <div>
                    {images.length ? <h4>Uploaded Images:</h4> : ''}
                    <div className="thumbnails">
                        {images}
                    </div>
                </div>
            </div>
        );
    }
});

var PredictImages = React.createClass({
    getInitialState: function() {
        return {};
    },

    predict: function() {
        var formData = new FormData(),
            props = this.props,
            self = this,
            files = this.props.ensemble.get('fileSet'),
            ensemble = this.props.ensemble;
        for (var i=0; i<files.length; i++) {
            formData.append('file-' + i, files[i]);
            files[i].internalName = 'file-' + i;
        }
        formData.append('iterations', JSON.stringify(ensemble.getIterationsForPredict(), null, 2));
        this.setState({ajaxPredictProcessing: true});
        $.ajax({
            url: '/api/predict/',
            type: 'POST',
            data: formData,
            cache: false,
            contentType: false,
            processData: false
        }).done(function(data) {
            ensemble.predicts.add(data);
            console.log('success');
            var predict = ensemble.predicts.get(data.id);
            predict.set('fileSet', files);
            ensemble.set('fileSet', []);
            self.setState({ajaxPredictProcessing: false});
            props.handlePredict();
        }).fail(function (xhr) {
            console.log('fail');
            self.setState({ajaxPredictProcessing: false});
        });
    },

    handleClear: function() {
        this.props.ensemble.set('fileSet', []);
    },

    handleForceUpdate: function() {
        this.forceUpdate();
    },

    render: function() {
        var clearBtn = null;

        if (this.props.ensemble.get('fileSet').length) {
            clearBtn = (
                <button className="btn btn-warning" onClick={this.handleClear}>
                    <i className="icon icon-white icon-remove"></i> Clear
                </button>
            );
        }

        if (this.state.ajaxPredictProcessing) {
            return <div className="ajax-loader"></div>;
        }

        return (
            <div>
                <Dropbox ref="dropbox" ensemble={this.props.ensemble} parentForceUpdate={this.handleForceUpdate}/>
                <button className="btn btn-info" onClick={this.predict}>
                    <i className="icon icon-white icon-play"></i> Go Predict
                </button> {clearBtn}
            </div>
        );
    }
});

var GeneralTab = React.createClass({
    render: function() {
        var body = null,
            models = this.props.ensemble.models.filter(function(model) {
                return model.get('isSelected');
            });
        if (models.length === 0) {
            return (
                        <h4 className="warning-message">
                            <i className="icon icon-white icon-warning-sign"></i>
                            At least one model needed for prediction
                        </h4>
                    );
        }
        if (this.props.selectedTask === 'input_data') {
            if (this.props.ensemble.get('data_type') === "IMAGES") {
                body = <PredictImages handlePredict={this.props.handlePredict} ensemble={this.props.ensemble} />;
            } else {
                body = <PredictInputData handlePredict={this.props.handlePredict} ensemble={this.props.ensemble} />;
            }
        } else {
            if (this.props.ensemble.get('possibleDatasets')) {
                body = <PredictDataset handlePredict={this.props.handlePredict} ensemble={this.props.ensemble}/>;
            } else {
                body = <div className="ajax-loader"></div>;
            }
        }
        return (
            <div>
                <PredictEnsembleInfoReact ensemble={this.props.ensemble} models={models}/>
                {body}
            </div>
        );
    }
});

var InputDataResultsTab = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return this.props.ensemble.predicts;
    },

    render: function() {
        var ensemble = this.props.ensemble,
            predicts = ensemble.getInputDataPredicts();
        var predictList = predicts.map(function(predict) {
            return (
                <AccordionGroupReact predict={predict} key={predict.id} ensemble={ensemble}/>
            );
        });
        return (
            <div>
                <div className="dm-header">
                    <div className="row-fluid">
                        <div className="span2"><span className="dm-col-offset">Predict #</span></div>
                        <div className="span7">Status</div>
                        <div className="span3 text-right"><span className="dm-col-offset-right">Actions</span></div>
                    </div>
                </div>
                <div className="accordion" id="predict-list">
                    {predictList}
                </div>
            </div>
        );
    }
});

var ChartsTab = React.createClass({
    render: function() {
        return (
            <div></div>
        );
    }
});

var SaveTab = React.createClass({
    render: function() {
        return (
            <div></div>
        );
    }
});

var DatasetResultsTab = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return this.props.ensemble.predicts;
    },

    render: function() {
        var ensemble = this.props.ensemble,
            predicts = ensemble.getDatasetsPredicts(),
            datasets = ensemble.get('possibleDatasets');
        var predictList = predicts.map(function(predict) {
            return (
                <AccordionGroupReact predict={predict} key={predict.id} ensemble={ensemble}/>
            );
        });
        return (
            <div>
                <div className="dm-header">
                    <div className="row-fluid">
                        <div className="span2"><span className="dm-col-offset">Predict #</span></div>
                        <div className="span7">Status</div>
                        <div className="span3 text-right"><span className="dm-col-offset-right">Actions</span></div>
                    </div>
                </div>
                <div className="accordion" id="predict-list">
                    {predictList}
                </div>
            </div>
        );
    }
});

var PredictTabsReact = React.createClass({
    getInitialState: function() {
        return {selectedTab: 'general'};
    },

    handleTabSelect: function(tab) {
        this.setState({selectedTab: tab});
    },

    render: function() {
        var body = null;
        switch(this.state.selectedTab) {
            case "general":
                body = <GeneralTab ensemble={this.props.ensemble} selectedTask={this.props.selectedTask} handlePredict={this.handleTabSelect.bind(this, 'results')}/>;
                break;
            case "results":
                if (this.props.selectedTask === 'input_data') {
                    body = <InputDataResultsTab ensemble={this.props.ensemble}/>;
                } else {
                    body = <DatasetResultsTab ensemble={this.props.ensemble}/>;
                }
                break;
            case "charts":
                body = <ChartsTab />;
                break;
            case "save":
                body = <SaveTab />;
                break;
        }
        return (
            <div>
                <ul className="tabs">
                    <li className={(this.state.selectedTab === 'general') ? "active" : ""} onClick={this.handleTabSelect.bind(this, 'general')}><i className="icon icon-white icon-tasks"></i> General</li>
                    <li className={(this.state.selectedTab === 'results') ? "active" : ""} onClick={this.handleTabSelect.bind(this, 'results')}><i className="icon icon-white icon-download"></i> Download Results</li>
                </ul>
                <div className="tabs-pane">
                    {body}
                </div>
            </div>
        );
    }
});

var ModelHead = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.model.stats];
    },

    handleChangeIteration: function(e) {
        this.props.model.set('selectedIter', this.props.model.stats.get(e.target.value));
    },

    handleToggleSelect: function(e) {
        if (this.props.ensemble.get('data_type') === 'IMAGES') {
            this.props.ensemble.models.forEach(function(model) {
                model.set('isSelected', false);
            });
        }
        this.props.model.set('isSelected', e.target.checked);
    },

    render: function() {
        var iters = null,
            accuracy = null,
            model = this.props.model,
            stat, options,
            selectedIter = model.get('selectedIter') || model.stats.last();
        if (model.stats.length > 0) {
            stat = model.stats.last();
            if (model.get('model_name') === 'MRNN') {
                options = this.props.model.stats.map(function(stat) {
                    return <option key={stat.id} value={stat.id}>{stat.get('iteration')}</option>;
                }).reverse();
                iters = (
                    <div>
                        <div>
                            <strong>Iteration:</strong>
                            <select value={selectedIter.id} onChange={this.handleChangeIteration} >
                                {options}
                            </select>
                        </div>
                        <div>
                            <strong>Iteration ID:</strong> {selectedIter.id}
                        </div>
                    </div>
                );
            } else {
                iters = <div><strong>Iteration:</strong> {stat.get('iteration')}</div>;
            }
            accuracy = <div><strong>Test/Train:</strong> {stat.getTestAccuracy()}% / {stat.getTrainAccuracy()}%</div>;
        }
        var modelID = (
            <div>
                <strong>Model ID:</strong> {model.id}
            </div>
        );
        return (
            <li>
                <input type="checkbox" checked={model.get('isSelected')} className="pull-right" onChange={this.handleToggleSelect}/>
                <h4 className="model-list-item">{(model.get('name')) ? model.get('name') : "Model " + model.id }</h4>
                {(model.get('name')) ? modelID : null }
                <div><strong>Net:</strong> {this.props.ensemble.modelNames[this.props.model.get('model_name')]}</div>
                {iters}
                {accuracy}
            </li>
        );
    }
});

var CurrentPredictStatus = React.createClass({
    render: function() {
        var state = this.props.state, classes = '';
        if (state === 'PREDICT') {
            classes = 'info';
        } else if (state === 'FINISHED') {
            classes = 'success';
        } else if (state === 'NEW' || state === 'QUEUE') {
            classes = 'warning';
        } else if (state === 'ERROR') {
            classes = 'important';
        }
        if (state === 'QUEUE') {
            state = 'In queue';
        }
        return (
            <span className={'label label-' + classes}>{state}</span>
        );
    }
});

var MRNNSample = React.createClass({
    render: function() {
        var output = this.props.data.map(function(timestep, i) {
            return <span key={i}>{timestep.join(', ') + ';'}</span>;
        });
        return <p>{output}</p>;
    }
});

var MRNNPredictOutput = React.createClass({
    render: function() {
        var output = this.props.data.map(function(sample, i) {
            return <MRNNSample key={i} data={sample} />;
        });
        return <div>{output}</div>;
    }
});

var GeneralPredictOutput = React.createClass({
    render: function() {
        var rows = this.props.data.map(function(row){
            return <p>{row.join(', ')}</p>
            });
        return <div>{rows}</div>;
    }
});

var ImagesLabels = React.createClass({
    render: function() {
        var output = this.props.data.map(function(label, i) {
            return <p key={i}><strong>{label[1]}:</strong> {label[0]}</p>;
        });
        return <div className="images-output-info">{output}</div>;
    }
});

var ImagesPredictOutput = React.createClass({
    render: function() {
        var files = {},
            src,
            image = null,
            fileSet = this.props.predict.get('fileSet');
        if (fileSet) {
            fileSet.forEach(function(file) {
                files[file.internalName] = file;
            });
        }
        var output = this.props.data.map(function(sample, i) {
            var filename = sample.filename.split('--')[0];
            try {
                src = files[filename].srcLink;
            } catch(e) {
                src = "";
            }
            if (src !== '') {
                image = <img src={src} />;
            }
            filename = sample.filename.split('--').slice(1).join('');
            return (
                <div key={sample.filename} className="thumbnails-item">
                    <span className="thumbnails-img">{image}</span>
                    <div className="images-output">
                        <div className="thumbnails-file">
                            <i className="icon icon-white icon-picture"></i>
                            <strong>Filename:</strong>
                            <span className="thumbnails-filename" title={filename}>{filename}</span>
                        </div>
                        <ImagesLabels data={sample.labels} />
                    </div>
                </div>
            );
        });
        return <div className="images-upload">{output}</div>;
    }
});

var PredictOutput = React.createClass({
    render: function() {
        var output;
        switch(this.props.ensemble.get('data_type')) {
            case 'TIMESERIES':
                output = <MRNNPredictOutput data={this.props.data} />;
                break;
            case 'GENERAL':
                output = <GeneralPredictOutput data={this.props.data} />;
                break;
            case 'IMAGES':
                output = <ImagesPredictOutput data={this.props.data} predict={this.props.predict}/>;
                break;
            default:
                output = null;
        }
        return output;
    }
});

var AccordionBodyReact = React.createClass({
    render: function() {
        var predict = this.props.predict,
            body = null,
            ensemble = this.props.ensemble,
            predictionResults = predict.get('results'),
            results = null,
            ensRes = null,
            averageResult = null,
            output = null;

        if (predictionResults) {
            if (ensemble.get('data_type') != 'IMAGES') {
                if (predict.get('dataset')) {
                    ensRes = (
                        <a className="btn btn-mini btn-warning" href={predictionResults.ensemble_prediction}>
                            <i className="icon icon-white icon-download"></i> Download
                        </a>
                    );
                } else {
                    ensRes = <PredictOutput data={predictionResults.ensemble_prediction} ensemble={ensemble} />;
                }
                averageResult = (
                    <div className="row-fluid predict-row">
                        <div className="span9 offset2">
                            <h4>Ensemble Prediction:</h4>
                            <div className="predict-output">{ensRes}</div>
                        </div>
                    </div>
                );
            }

            results = predictionResults.predictions.map(function(result) {
                if (predict.get('dataset')) {
                    output = (
                        <a className="btn btn-mini btn-warning" href={result.output}>
                            <i className="icon icon-white icon-download"></i> Download
                        </a>
                    );
                } else {
                    output = <PredictOutput data={result.output} ensemble={ensemble} predict={predict} />;
                }
                return (
                    <div key={result.iteration} className="row-fluid predict-row">
                        <div className="span9 offset2">
                            <h4>Output:</h4>
                            <div className="predict-output">{output}</div>
                        </div>
                    </div>
                );
            }, this);
        }

        if (predict.get('state') === 'FINISHED') {
            body = (
                <div id={predict.id} className="accordion-body collapse">
                    <div className="accordion-inner">
                        <div className={predict.get('dataset') ? "dm-details dm-details-download" : "dm-details"}>
                            {results}
                            {averageResult}
                        </div>
                    </div>
                </div>
            );
        }

        return (
            <div>{body}</div>
        );
    }
});

var AccordionHeadReact = React.createClass({
    deletePredict: function(e) {
        e.stopPropagation();
        var predict = this.props.predict,
            props = this.props;
        predict.beforeDeleteRequest();
        $.ajax({
            url: '/api/predict/' + predict.id + '/',
            type: 'DELETE',
            dataType: 'json'
        }).done(function (data) {
            props.ensemble.predicts.remove(predict);
        }).fail(function (xhr) {
            predict.deleteRequestFail();
        });
    },

    render: function() {
        var predict = this.props.predict, resultsBtn = null;

        if (predict.get('state') === 'FINISHED') {
            resultsBtn = (
                <span className="btn btn-mini btn-info">
                    <i className="icon icon-white icon-info-sign"></i>Results
                </span>
            );
        }

        var deleteBtn = (
            <span className="btn btn-mini btn-danger" onClick={this.deletePredict}>
                <i className="icon icon-white icon-trash"></i>Remove
            </span>
        );

        var head = (
            <a className="accordion-toggle collapsed" data-toggle="collapse"
                                                      data-parent="#predict-list"
                                                      href={"#" + predict.id}>
                <div className="dm-item">
                    <div className="row-fluid">
                        <div className="span2"><strong className="dm-col-offset">{predict.id}</strong></div>
                        <div className="span7">
                            <CurrentPredictStatus state={predict.get('state')} />
                        </div>
                        <div className="span3 text-right">
                            <span className="dm-col-offset-right">
                                {resultsBtn} {deleteBtn}
                            </span>
                        </div>
                    </div>
                </div>
            </a>
        );

        return (
            <div className="accordion-heading">
                {head}
            </div>
        );
    }
});

var AccordionGroupReact = React.createClass({
    render: function() {
        return (
            <div className="accordion-group">
                <AccordionHeadReact predict={this.props.predict} ensemble={this.props.ensemble}/>
                <AccordionBodyReact predict={this.props.predict} ensemble={this.props.ensemble}/>
            </div>
        );
    }
});

var PredictModelsReact = React.createClass({
    render: function() {
        var props = this.props;
        var modelsHeads = props.ensemble.models.map(function(model) {
            return <ModelHead key={model.id} model={model} ensemble={props.ensemble} />;
        });

        return (
            <div className="panel panel-predict">
                <div className="panel-heading">
                    <h2>Select the models you'd like to use in this prediction</h2>
                </div>
                <div className="panel-body">
                    <ul className="models-list-ul">
                        {modelsHeads}
                    </ul>
                </div>
            </div>
        );
    }
});

var PredictReact = React.createClass({
    mixins: [Utils.BackboneMixin],

    getBackboneModels: function() {
        return [this.props.ensemble, this.props.ensemble.models];
    },

    render: function() {
        var props = this.props,
            ensembleState = props.ensemble.get('state');
        if (!this.props.loaded) {
            return <div className="ajax-loader"></div>;
        } else if (props.ensemble.get('state') !== 'finished') {
            return <div>Finish ensemble before predict</div>;
        }
        return <PredictWizardReact ensemble={this.props.ensemble} />;
    }
});

module.exports = PredictReact;
